/*
 * This file is part of Cockpit.
 *
 * Copyright (C) 2016 Red Hat, Inc.
 *
 * Cockpit is free software; you can redistribute it and/or modify it
 * under the terms of the GNU Lesser General Public License as published by
 * the Free Software Foundation; either version 2.1 of the License, or
 * (at your option) any later version.
 *
 * Cockpit is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public License
 * along with Cockpit; If not, see <http://www.gnu.org/licenses/>.
 */

const cockpit = require("cockpit");
import * as PK from "packagekit";

const _ = cockpit.gettext;

function createProxy(name) {
    let service = cockpit.dbus('com.redhat.RHSM1', {'superuser': 'require'});
    return service.proxy(`com.redhat.RHSM1.${name}`, `/com/redhat/RHSM1/${name}`);
}

// creates multiple services otherwise only readies one proxy at a time
const configService = createProxy('Config');
const registerServer = createProxy('RegisterServer');
const attachService = createProxy('Attach');
const entitlementService = createProxy('Entitlement');
const unregisterService = createProxy('Unregister');
const productsService = createProxy('Products');
const consumerService = createProxy('Consumer');
const syspurposeService = createProxy('Syspurpose');

const client = { };

const userLang = navigator.language || navigator.userLanguage;

cockpit.event_target(client);

client.subscriptionStatus = {
    status: undefined,
    status_msg: _('Unknown'),
    products: [],
    error: undefined,
    org: undefined,
};

client.config = {
    loaded: false,
};

client.syspurposeStatus = {
    info : {
        "service_level_agreement" : null,
        "usage" : null,
        "role" : null,
        "addons" : null,
    },
    status : null,
};

client.insightsAvailable = false;
client.insightsPackage = "insights-client";

const RHSM_DEFAULTS = { // TODO get these from a d-bus service instead
    hostname: 'subscription.rhsm.redhat.com',
    port: '443',
    prefix: '/subscription',
    proxy_port: '3128',
};

// we trigger an event called "dataChanged" when the data has changed

function needRender() {
    let event = document.createEvent("Event");
    event.initEvent("dataChanged", false, false);
    client.dispatchEvent(event);
}

/* we trigger status update via dbus
 * if we don't get a timely reply, consider subscription-manager failure
 */

function parseProducts(text) {
    const products = JSON.parse(text);
    return products.map(function(product) {
        return {
            'productName': product[0],
            'productId': product[1],
            'version': product[2],
            'arch': product[3],
            'status': product[4],
            'status_details': product[5],
            'starts': product[6],
            'ends': product[7]
        };
    });
}

// Error message produced by D-Bus API should be string containing
// regular JSON with following format:
// {"exception": "NameOfException", "message": "Some error message"}
// Only message should be reported to user.
function parseErrorMessage(error) {
    let err_msg;
    try {
        err_msg = JSON.parse(error).message;
    } catch (parse_err) {
        console.log('Error parsing D-Bus error message: ', parse_err.message);
        console.log('Returning original error message: ', error);
        err_msg = error;
    }
    return err_msg;
}

// Parse error severity
function parseErrorSeverity(error) {
    let severity;
    try {
        severity = JSON.parse(error).severity;
    } catch (parse_err) {
        console.log('Error parsing D-Bus error message: ', parse_err.message);
        console.log('Returning default error severity: error');
        severity = "error";
    }
    return severity;
}

/**
 * Method that calls a method on a dbus service proxy, only if it is available.
 *
 * If the service does not contain the provided method, we try to restart the rhsm service,
 * and if the restart is successful, we call the delegate method; otherwise, we fail gracefully.
 *
 * @param serviceProxy a dbus service proxy
 * @param methodName a method on the provided serviceProxy
 * @param delegateMethod the method that we delegate the actual call to dbus
 */
function safeDBusCall(serviceProxy, delegateMethod) {
    return serviceProxy.wait()
            .then(delegateMethod)
            .fail(ex => {
                console.debug(ex);
            });
}

let gettingDetails = false;
let getDetailsRequested = false;
function getSubscriptionDetails() {
    if (isRegistering) {
        return;
    }
    if (gettingDetails) {
        getDetailsRequested = true;
        return;
    }
    getDetailsRequested = false;
    gettingDetails = true;
    safeDBusCall(productsService, () => {
        productsService.ListInstalledProducts('', {}, userLang) // FIXME: use proxy settings
                .then(result => {
                    client.subscriptionStatus.products = parseProducts(result);
                })
                .catch(error => {
                    client.subscriptionStatus.error = {
                        'severity': parseErrorSeverity(error),
                        'msg': parseErrorMessage(error)
                    };
                })
                .then(() => {
                    gettingDetails = false;
                    if (getDetailsRequested)
                        getSubscriptionDetails();
                    needRender();
                });
    });
}

/* convenience function for specifying d-bus strings */
function dbus_str(value) {
    return {
        t: 's',
        v: value,
    };
}

/* convenience function for specifying d-bus boolean */
function dbus_bool(value) {
    return {
        t: 'b',
        v: value,
    };
}

client.closeRegisterDialog = false;
let isRegistering = false;

/* Overall flow is as follows:

Preconditions:
 - subscriptionDetails is populated with values from the config file
 - subscriptionDetails is then modified by UI interaction

1. connection_options is populated with default values
2. connection_options is updated by subscriptionDetails; if an option isn't specified, it remains the default.
3. if an option is different than what's in the config, we set the config option
 */
client.registerSystem = (subscriptionDetails, update_progress) => {
    const dfd = cockpit.defer();
    // Note: when values are not specified we force use of default
    // values. Otherwise old and obsolete values from rhsm.conf could be used.
    const connection_options = {
        host: dbus_str(RHSM_DEFAULTS.hostname),
        port: dbus_str(RHSM_DEFAULTS.port),
        proxy_hostname: dbus_str(''),
        proxy_port: dbus_str(''),
        proxy_user: dbus_str(''),
        proxy_password: dbus_str(''),
        handler: dbus_str(RHSM_DEFAULTS.prefix),
    };

    if (subscriptionDetails.activation_keys && !subscriptionDetails.org) {
        const error = new Error("'Organization' is required when using activation keys...");
        dfd.reject(error);
        return dfd.promise();
    }

    if (subscriptionDetails.url !== 'default') {
        /*  parse url into host, port, handler; sorry about the ugly regex */
        const pattern = new RegExp(
            '^' +
            '(?:https?://)?' +              // protocol (optional)
            '(?:\\[([^\\]]+)\\])?' +        // ipv6 address (optional)
            '(?:([^/:]+))?' +               // hostname/ipv4 address (optional)
            '(?::(?=[0-9])([0-9]+))?' +     // port (optional)
            '(?:(/.+))?' +                  // path (optional)
            '$'
        );
        const match = pattern.exec(subscriptionDetails.server_url); // TODO handle failure
        const ipv6Address = match[1];
        const address = match[2];
        const port = match[3];
        const path = match[4];
        if (ipv6Address && address) {
            throw 'malformed server url; ipv6 address syntax and hostname are mutually exclusive';
        }
        if (ipv6Address) {
            connection_options.host = dbus_str(ipv6Address);
        }
        if (address) {
            connection_options.host = dbus_str(address);
        }
        if (port) {
            connection_options.port = dbus_str(port);
        }
        if (path) {
            connection_options.handler = dbus_str(path);
        }
    }

    // proxy is optional
    if (subscriptionDetails.proxy) {
        if (subscriptionDetails.proxy_server) {
            const pattern = new RegExp(
                '^' +
                '(?:\\[([^\\]]+)\\])?' +    // ipv6 address (optional)
                '(?:([^/:]+))?' +           // hostname/ipv4 address (optional)
                '(?::(?=[0-9])([0-9]+))?' + // port (optional)
                '$'
            );
            const match = pattern.exec(subscriptionDetails.proxy_server);
            const ipv6Address = match[1];
            const address = match[2];
            let port = match[3];
            if (ipv6Address && address) {
                throw 'malformed proxy url; ipv6 address syntax and hostname are mutually exclusive';
            }
            if (ipv6Address) {
                connection_options.proxy_hostname = dbus_str(ipv6Address);
            }
            if (address) {
                connection_options.proxy_hostname = dbus_str(address);
            }
            if (!port) {
                port = RHSM_DEFAULTS.proxy_port;
            }
            if (port) {
                connection_options.proxy_port = dbus_str(port);
            }
        }
        if (subscriptionDetails.proxy_user) {
            connection_options.proxy_user = dbus_str(subscriptionDetails.proxy_user);
        }
        if (subscriptionDetails.proxy_password) {
            connection_options.proxy_password = dbus_str(subscriptionDetails.proxy_password);
        }
    }

    console.debug('connection_options:', connection_options);
    isRegistering = true;

    registerServer.wait(() => {
        if (update_progress)
            update_progress(_("Starting registration service ..."), null);
        let registered = false;
        registerServer.Start(userLang)
                .then(socket => {
                    console.debug('Opening private bus interface at ' + socket);
                    const private_interface = cockpit.dbus(
                        null,
                        {
                            bus: 'none',
                            address: socket,
                            superuser: 'require'
                        }
                    );
                    const registerService = private_interface.proxy(
                        'com.redhat.RHSM1.Register',
                        '/com/redhat/RHSM1/Register'
                    );
                    const registration_options = {
                        "enable_content": dbus_bool(subscriptionDetails.auto_attach)
                    };
                    console.log('registration_options:', registration_options);
                    if (subscriptionDetails.activation_keys) {
                        if (update_progress)
                            update_progress(_("Registering using activation key ..."), null);
                        console.debug('registering using activation key');
                        let result = registerService.call(
                            'RegisterWithActivationKeys',
                            [
                                subscriptionDetails.org,
                                subscriptionDetails.activation_keys.split(','),
                                registration_options,
                                connection_options,
                                userLang
                            ]
                        );
                        registered = true;
                        return result;
                    }
                    else {
                        console.debug('registering using username and password');
                        if (update_progress)
                            update_progress(_("Registering using username and password ..."), null);
                        let result = registerService.call(
                            'Register',
                            [
                                subscriptionDetails.org,
                                subscriptionDetails.user,
                                subscriptionDetails.password,
                                registration_options,
                                connection_options,
                                userLang
                            ]
                        );
                        registered = true;
                        return result;
                    }
                })
                .catch(error => {
                    console.error('error registering', error);
                    isRegistering = false;
                    registered = false;
                    dfd.reject(parseErrorMessage(error));
                })
                .then(result => {
                    console.debug('Result of registration: ', result);
                    if (result) {
                        let consumer = JSON.parse(result);
                        client.org = consumer.owner;
                    }
                    if (update_progress)
                        update_progress(_("Stopping registration service ..."), null);
                    console.debug('stopping registration server');
                    return registerServer.Stop(userLang);
                })
                .catch(error => {
                    console.error('error stopping registration bus', error);
                    isRegistering = false;
                    dfd.reject(parseErrorMessage(error));
                })
                .then(() => {
                    if (registered) {
                    // Dictionary (key: client.config / rhsm.conf options, value are
                    // attributes of connection_options) ... ('handler' and 'host' are different)
                    // Note: only options from [server] section are supported
                        let dict = {
                            'hostname': 'host',
                            'port': 'port',
                            'prefix': 'handler',
                            'proxy_hostname': 'proxy_hostname',
                            'proxy_port': 'proxy_port',
                            'proxy_user': 'proxy_user',
                            'proxy_password': 'proxy_password',
                        };
                        if (update_progress)
                            update_progress(_("Saving configuration ..."), null);
                        Object.keys(dict).forEach(function (key) {
                        // Is config option in dialog different from  rhsm.conf
                            if (client.config[key] !== connection_options[dict[key]].v) {
                                console.debug('saving: server.' + key, connection_options[dict[key]]);
                                configService.Set('server.' + key, connection_options[dict[key]], userLang)
                                        .catch(error => {
                                            console.error('unable to save server.' + key, error);
                                        });
                            }
                        });
                    }
                })
                .catch(error => {
                    console.error('error during auto-attach', error);
                    isRegistering = false;
                    dfd.reject(parseErrorMessage(error));
                })
                .then(() => {
                    if (update_progress)
                        update_progress(_("Updating status ..."), null);
                    client.closeRegisterDialog = true;
                    isRegistering = false;
                    console.debug('requesting update of subscription status');
                    requestSubscriptionStatusUpdate().always(() => {
                        dfd.resolve();
                    });
                    console.debug('requesting update of syspurpose status');
                    requestSyspurposeStatusUpdate().always(() => {
                        dfd.resolve();
                    });
                });
    });
    return dfd.promise();
};

client.unregisterSystem = () => {
    client.subscriptionStatus.status = "unregistering";
    client.subscriptionStatus.status_msg = _("Unregistering");
    needRender();
    unregisterService.wait(() => {
        unregisterService.Unregister({}, userLang) // FIXME: use proxy settings
                .catch(error => {
                    console.error('error unregistering system', error);
                    client.subscriptionStatus.error = {
                        'severity': parseErrorSeverity(error),
                        'msg': parseErrorMessage(error)
                    };
                })
                .always(() => {
                    console.debug('requesting update');
                    requestSubscriptionStatusUpdate();
                });
    });
};

client.autoAttach = () => {
    const dfd = cockpit.defer();
    console.debug('auto-attaching ...');
    attachService.AutoAttach('', {}, userLang)
            .catch(error => {
                console.error('error during auto-attach', error);
                client.subscriptionStatus.error = {
                    'severity': parseErrorSeverity(error),
                    'msg': parseErrorMessage(error)
                };
            })
            .then(() => {
                dfd.resolve();
                needRender();
            });
    return dfd.promise();
};

function statusUpdateFailed(reason) {
    console.warn("Subscription status update failed:", reason);
    client.subscriptionStatus.status = (reason && reason.problem) || "not-found";
    client.subscriptionStatus.status_msg = (reason && reason.problem) || _("not-found");
    needRender();
}

function requestSubscriptionStatusUpdate() {
    return client.getSubscriptionStatus()
            .catch(ex => statusUpdateFailed(ex));
}

function requestCurrentOrgUpdate() {
    return client.getCurrentOrg()
            .catch(ex => statusUpdateFailed(ex));
}

function requestSyspurposeStatusUpdate() {
    return client.getSyspurposeStatus()
            .catch(ex => statusUpdateFailed(ex));
}

function requestSyspurposeUpdate() {
    return client.getSyspurpose()
            .catch(ex => statusUpdateFailed(ex));
}

/* get subscription summary */
client.getSubscriptionStatus = function() {
    let dfd = cockpit.defer();
    safeDBusCall(entitlementService, () => {
        entitlementService.GetStatus('', userLang)
                .then(result => {
                    let parsed = false;
                    let system_status;
                    try {
                        system_status = JSON.parse(result);
                        parsed = true;
                    } catch (err) {
                        client.subscriptionStatus.status = "unknown";
                        client.subscriptionStatus.status_msg = _("Corrupted JSON with status");
                    }
                    if (parsed === true) {
                        /* status contains ID of status */
                        client.subscriptionStatus.status = system_status.status_id;
                        /* status contains string that can be localized */
                        client.subscriptionStatus.status_msg = system_status.status;
                        if (client.closeRegisterDialog) {
                            client.closeRegisterDialog = false;
                        }
                        dfd.resolve();
                    }
                })
                .catch(ex => {
                    console.debug(ex);
                    client.subscriptionStatus.status = "unknown";
                    client.subscriptionStatus.status_msg = _("Unknown");
                })
                .then(() => {
                    getSubscriptionDetails();
                    needRender();
                });
    });
    return dfd.promise();
};

/**
 * Method for getting current organization (owner), when system is already
 * registered. When calling D-Bus method GetOrg is successful, then store
 * returned JSON document in client.org.
 */
client.getCurrentOrg = function () {
    let dfd = cockpit.defer();
    safeDBusCall(consumerService, () => {
        console.debug('Trying to get current organization...');
        consumerService.GetOrg(userLang)
                .then(result => {
                    let parsed;
                    console.debug('Current organization:', result);
                    try {
                        client.org = JSON.parse(result);
                        parsed = true;
                    } catch (err) {
                        console.error('Error: parsing JSON with organization', err.message);
                        parsed = false;
                    }
                    if (parsed) {
                        dfd.resolve();
                        needRender();
                    }
                })
                .catch(error => {
                    client.subscriptionStatus.error = {
                        'severity': parseErrorSeverity(error),
                        'msg': parseErrorMessage(error)
                    };
                });
    });
    return dfd.promise();
};

client.getSyspurposeStatus = () => {
    let dfd = cockpit.defer();
    if (isRegistering) { return dfd.promise(); }
    return safeDBusCall(syspurposeService, () => {
        syspurposeService.GetSyspurposeStatus(userLang)
                .then(result => {
                    client.syspurposeStatus.status = result;
                })
                .catch(ex => {
                    console.debug(ex);
                    client.syspurposeStatus.status = null; // TODO: change to something meaningful
                })
                .then(needRender);
    });
};

client.getSyspurpose = function() {
    let dfd = cockpit.defer();

    safeDBusCall(syspurposeService, () => {
        syspurposeService.GetSyspurpose(userLang)
                .then(result => {
                    client.syspurposeStatus.info = JSON.parse(result);
                    dfd.resolve();
                })
                .catch(ex => {
                    console.debug(ex);
                    client.syspurposeStatus.info = 'Unknown'; // TODO: change to something meaningful
                })
                .then(needRender);
    });

    return dfd.promise();
};

client.readConfig = function() {
    let dfd = cockpit.defer();

    safeDBusCall(configService, () => {
        console.debug('Reading configuration file');
        configService.GetAll(userLang).then(config => {
            const hostname = config.server.v.hostname;
            const port = config.server.v.port;
            const prefix = config.server.v.prefix;
            const proxyHostname = config.server.v.proxy_hostname;
            const proxyPort = config.server.v.proxy_port;
            const proxyUser = config.server.v.proxy_user;
            const proxyPassword = config.server.v.proxy_password;

            const usingDefaultUrl = (port === '443' &&
                hostname === RHSM_DEFAULTS.hostname &&
                port === RHSM_DEFAULTS.port &&
                prefix === RHSM_DEFAULTS.prefix
            );

            const maybePort = port === '443' ? '' : `:${port}`;
            const maybePrefix = prefix === '/subscription' ? '' : prefix;
            const hostnamePart = hostname.includes(':') ? `[${hostname}]`: hostname;
            const serverUrl = usingDefaultUrl ? '' : `${hostnamePart}${maybePort}${maybePrefix}`;
            const proxyHostnamePart = proxyHostname.includes(':') ? `[${proxyHostname}]` : proxyHostname;
            const usingProxy = proxyHostname !== '';
            const maybeProxyPort = proxyPort ? `:${proxyPort}`: '';
            const proxyServer = usingProxy ? `${proxyHostnamePart}${maybeProxyPort}`: '';

            // Note: we don't use camelCase, because we keep naming convention of rhsm.conf
            // Thus we can do some simplification of code
            Object.assign(client.config, {
                url: usingDefaultUrl ? 'default' : 'custom',
                hostname: hostname,
                port: port,
                prefix: prefix,
                server_url: serverUrl,
                proxy: usingProxy,
                proxy_server: proxyServer,
                proxy_hostname: proxyHostname,
                proxy_port: proxyPort,
                proxy_user: proxyUser,
                proxy_password: proxyPassword,
                loaded: true,
            });
            console.debug('loaded client config', client.config);
            dfd.resolve();
        }).catch(ex => {
            console.debug(ex);
        });
    });

    return dfd.promise();
};

client.toArray = obj => {
    /*
        checks if object passed in is an iterable or not
        see https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Iteration_protocols
        for more info
         */
    if (obj == null) {
        return [];
    }
    if (typeof obj === 'string') {
        return [obj];
    }
    if (typeof obj[Symbol.iterator] === 'function' ) {
        return Array.from(obj);
    }
};

const detectInsights = () => {
    return cockpit.spawn([ "which", "insights-client" ], { err: "ignore" }).then(
        () => client.insightsAvailable = true,
        () => {
            PK.detect().then(pk_available => {
                client.insightsAvailable = pk_available && client.insightsPackage;
            });
        });
};

const updateConfig = () => {
    return client.readConfig().then(detectInsights).then(needRender);
};

client.setError = (severity, message) => {
    client.subscriptionStatus.error = {
        severity: severity,
        msg: message
    };
    needRender();
};

client.init = () => {
    /* we want to get notified if subscription status of the system changes */
    entitlementService.addEventListener("EntitlementChanged", requestSubscriptionStatusUpdate);
    productsService.addEventListener("InstalledProductsChanged", requestSubscriptionStatusUpdate);
    consumerService.addEventListener("ConsumerChanged", requestSubscriptionStatusUpdate);

    // When consumer changed (system was registered/unregistered, then it is necessary to
    // get current organization)
    consumerService.addEventListener("ConsumerChanged", requestCurrentOrgUpdate);
    entitlementService.addEventListener("EntitlementChanged", requestCurrentOrgUpdate);

    configService.addEventListener("ConfigChanged", updateConfig);
    syspurposeService.addEventListener("SyspurposeChanged", requestSyspurposeUpdate);

    // We want to get notified if syspurpose status of the system changes (when either the syspurpose.json changed,
    // or our subscriptions changed, or we registered/unregistered).
    syspurposeService.addEventListener("SyspurposeChanged", requestSyspurposeStatusUpdate);
    entitlementService.addEventListener("EntitlementChanged", requestSyspurposeStatusUpdate);
    consumerService.addEventListener("ConsumerChanged", requestSyspurposeStatusUpdate);

    // get initial status
    requestCurrentOrgUpdate();
    requestSubscriptionStatusUpdate();
    requestSyspurposeUpdate();
    requestSyspurposeStatusUpdate();
    // read config (async)
    configService.wait().then(updateConfig);
};

export default client;
