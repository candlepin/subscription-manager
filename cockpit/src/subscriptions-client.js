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
const service = cockpit.dbus('com.redhat.RHSM1', {'superuser': 'require'});
const configService = service.proxy('com.redhat.RHSM1.Config', '/com/redhat/RHSM1/Config');
const registerServer = service.proxy('com.redhat.RHSM1.RegisterServer', '/com/redhat/RHSM1/RegisterServer');
const attachService = service.proxy('com.redhat.RHSM1.Attach', '/com/redhat/RHSM1/Attach');
const entitlementService = service.proxy('com.redhat.RHSM1.Entitlement', '/com/redhat/RHSM1/Entitlement');
const unregisterService = service.proxy('com.redhat.RHSM1.Unregister', '/com/redhat/RHSM1/Unregister');
const productsService = service.proxy('com.redhat.RHSM1.Products', '/com/redhat/RHSM1/Products');
const legacyService = cockpit.dbus('com.redhat.SubscriptionManager');  // FIXME replace?
const _ = cockpit.gettext;

const client = { };

cockpit.event_target(client);

client.subscriptionStatus = {
    serviceStatus: undefined,
    status: undefined,
    products: [],
    error: undefined,
};

client.config = {
    loaded: false,
};

const RHSM_DEFAULTS = { // TODO get these from a d-bus service instead
    hostname: 'subscription.rhsm.redhat.com',
    port: '443',
    prefix: '/subscription'
};

// we trigger an event called "dataChanged" when the data has changed

function needRender() {
    let ev = document.createEvent("Event");
    ev.initEvent("dataChanged", false, false);
    client.dispatchEvent(ev);
}

/* we trigger status update via dbus
 * if we don't get a timely reply, consider subscription-manager failure
 */
let updateTimeout;

function parseProducts(text) {
    const products = JSON.parse(text);
    return products.map(function(product) {
        return {
            'productName': product[0],
            'productId': product[1],
            'version': product[2],
            'arch': product[3],
            'status': product[4],
            'starts': product[6],
            'ends': product[7]
        };
    });
}

let gettingDetails = false;
let getDetailsRequested = false;
function getSubscriptionDetails() {
    if (gettingDetails) {
        getDetailsRequested = true;
        return;
    }
    getDetailsRequested = false;
    gettingDetails = true;
    productsService.wait(() => {
        productsService.ListInstalledProducts('', {})
            .then(result => {
                client.subscriptionStatus.products = parseProducts(result);
            })
            .catch(ex => {
                client.subscriptionStatus.error = ex;
            })
            .then(() => {
                gettingDetails = false;
                if (getDetailsRequested)
                    getSubscriptionDetails();
                needRender();
            });
    });
}

client.registerSystem = subscriptionDetails => {
    const dfd = cockpit.defer();
    const connection_options = {};

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
            connection_options.host = {
                t: 's',
                v: ipv6Address,
            };
        }
        if (address) {
            connection_options.host = {
                t: 's',
                v: address,
            };
        }
        // Note: when port or handler options are not specified, then we force use default
        // values. Otherwise old an obsolete values from rhsm.conf could be used.
        if (port) {
            connection_options.port = {
                t: 's',
                v: port,
            };
        } else {
            connection_options.port = {
                t: 's',
                v: RHSM_DEFAULTS.port
            };
        }
        if (path) {
            connection_options.handler = {
                t: 's',
                v: path,
            };
        } else {
            connection_options.handler = {
                t: 's',
                v: RHSM_DEFAULTS.prefix,
            };
        }
    }
    else {
        connection_options.host = {
            t: 's',
            v: RHSM_DEFAULTS.hostname,
        };
        connection_options.port = {
            t: 's',
            v: RHSM_DEFAULTS.port,
        };
        connection_options.handler = {
            t: 's',
            v: RHSM_DEFAULTS.prefix,
        };
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
            const port = match[3];
            if (ipv6Address && address) {
                throw 'malformed proxy url; ipv6 address syntax and hostname are mutually exclusive';
            }
            if (ipv6Address) {
                connection_options.proxy_hostname = {
                    t: 's',
                    v: ipv6Address,
                };
            }
            if (address) {
                connection_options.proxy_hostname = {
                    t: 's',
                    v: address,
                };
            }
            if (port) {
                connection_options.proxy_port = {
                    t: 's',
                    v: port,
                };
            }
        }
        if (subscriptionDetails.proxy_user) {
            connection_options.proxy_user = {
                t: 's',
                v: subscriptionDetails.proxy_user,
            };
        }
        if (subscriptionDetails.proxy_password) {
            connection_options.proxy_password = {
                t: 's',
                v: subscriptionDetails.proxy_password,
            };
        }
    }

    console.debug('connection_options:', connection_options);

    registerServer.wait(() => {
        let registered = false;
        registerServer.Start()
            .then(socket => {
                console.debug('Opening private bus interface at ' + socket);
                const private_interface = cockpit.dbus(null, {bus: 'none', address: socket, superuser: 'require'});
                const registerService = private_interface.proxy(
                    'com.redhat.RHSM1.Register',
                    '/com/redhat/RHSM1/Register'
                );
                registered = true;
                if (subscriptionDetails.activation_keys) {
                    return registerService.call(
                        'RegisterWithActivationKeys',
                        [
                            subscriptionDetails.org,
                            subscriptionDetails.activation_keys.split(','),
                            {},
                            connection_options
                        ]);
                }
                else {
                    return registerService.call(
                        'Register',
                        [
                            subscriptionDetails.org,
                            subscriptionDetails.user,
                            subscriptionDetails.password,
                            {},
                            connection_options
                        ]);
                }
            })
            .catch(error => {
                console.error('error registering', error);
                registered = false;
                dfd.reject(error);
            })
            .then(() => {
                console.debug('stopping registration server');
                return registerServer.Stop();
            })
            .catch(error => {
                console.error('error stopping registration bus', error);
                dfd.reject(error);
            })
            .then(() => {
                if (registered === true) {
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
                    // for (let key in dict) {
                    Object.keys(dict).forEach(function (key) {
                        // To be sure that config option was loaded from rhsm.conf
                        if (client.config.hasOwnProperty(key)) {
                            // Was this config option specified in dialog?
                            if (connection_options.hasOwnProperty(dict[key])) {
                                // Is config option in dialog different from  rhsm.conf
                                if (client.config[key] !== connection_options[dict[key]].v) {
                                    console.debug('saving: server.' + key, connection_options[dict[key]]);
                                    configService.Set('server.' + key, connection_options[dict[key]])
                                        .catch(error => {
                                            console.error('unable to save server.' + key, error);
                                        });
                                }
                            } else {
                                let default_value = '';
                                if (RHSM_DEFAULTS.hasOwnProperty(key)) {
                                    default_value = RHSM_DEFAULTS[key];
                                }
                                // When config option was not specified in dialog, then it is
                                // necessary to reset it in rhsm.conf (e.g. proxy options are optional)
                                console.debug('resetting: server.' + key);
                                configService.Set('server.' + key, {'t': 's', 'v': default_value})
                                    .catch(error => {
                                        console.error('unable to reset server.' + key, error);
                                    });
                            }
                        }
                    });

                    // When system is registered and config options are saved,
                    // then we can try to auto-attach
                    console.debug('auto-attaching');
                    if (connection_options.proxy_hostname) {
                        var proxy_options = {};
                        proxy_options.proxy_hostname = connection_options.proxy_hostname;
                        if (connection_options.proxy_port) {
                            // FIXME: change D-Bus implementation to be able to use string too
                            proxy_options.proxy_port = {
                                't': 'i',
                                'v': Number(connection_options.proxy_port.v)
                            };
                        }
                        if (connection_options.proxy_user) {
                            proxy_options.proxy_user = connection_options.proxy_user;
                        }
                        if (connection_options.proxy_password) {
                            proxy_options.proxy_password = connection_options.proxy_password;
                        }
                        attachService.AutoAttach('', proxy_options)
                            .catch(error => {
                                console.error('error during autoattach', error);
                                dfd.reject(error);
                            });
                    } else {
                        attachService.AutoAttach('', {})
                            .catch(error => {
                                console.error('error during autoattach', error);
                                dfd.reject(error);
                            });
                    }
                }
            })
            .always(() => {
                console.debug('requesting update');
                requestUpdate();
                dfd.resolve();
            });
    });

    requestUpdate();
    return dfd.promise();
};

client.unregisterSystem = () => {
    client.subscriptionStatus.status = "Unregistering";
    needRender();
    unregisterService.wait(() => {
        unregisterService.Unregister({})
            .always(() => {
                requestUpdate();
            });
    });
};

/* request update via DBus
 * possible status values: https://github.com/candlepin/subscription-manager/blob/30c3b52320c3e73ebd7435b4fc8b0b6319985d19/src/rhsm_icon/rhsm_icon.c#L98
 * [ RHSM_VALID, RHSM_EXPIRED, RHSM_WARNING, RHN_CLASSIC, RHSM_PARTIALLY_VALID, RHSM_REGISTRATION_REQUIRED ]
 */
const subscriptionStatusValues = [
    'RHSM_VALID',
    'RHSM_EXPIRED',
    'RHSM_WARNING',
    'RHN_CLASSIC',
    'RHSM_PARTIALLY_VALID',
    'RHSM_REGISTRATION_REQUIRED'
];
function requestUpdate() {
    legacyService.wait(() => {
        legacyService.call('/EntitlementStatus',
            'com.redhat.SubscriptionManager.EntitlementStatus',
            'check_status',
            []
        )
            .always(() => {
                window.clearTimeout(updateTimeout);
            })
            .done(result => {
                client.subscriptionStatus.serviceStatus = subscriptionStatusValues[result[0]];
                client.getSubscriptionStatus();
            })
            .catch(ex => {
                statusUpdateFailed("EntitlementStatus.check_status() failed:", ex);
            });

        /* TODO: Don't use a timeout here. Needs better API */
        updateTimeout = window.setTimeout(() => {
            statusUpdateFailed("timeout");
        }, 60000);
    });
}

let gettingStatus = false;
/* get subscription summary */
client.getSubscriptionStatus = () => {
    if (gettingStatus) {
        return;
    }
    gettingStatus = true;

    entitlementService.wait(() => {
        entitlementService.GetStatus('')
            .then(result => {
                const status = JSON.parse(result);
                client.subscriptionStatus.status = status.status;
            })
            .catch(() => {
                client.subscriptionStatus.status = 'Unknown';
            })
            .then(() => {
                gettingStatus = false;
                getSubscriptionDetails();
                needRender();
            });
    });
};

client.readConfig = () => {
    return configService.wait(() => configService.GetAll().then(config => {
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
    }));
};

client.init = () => {
    /* we want to get notified if subscription status of the system changes */
    legacyService.subscribe(
        { path: '/EntitlementStatus',
          interface: 'com.redhat.SubscriptionManager.EntitlementStatus',
          member: 'entitlement_status_changed'
        },
        () => {
            window.clearTimeout(updateTimeout);
            /*
             * status has changed, now get actual status via command line
             * since older versions of subscription-manager don't deliver this via DBus
             * note: subscription-manager needs superuser privileges
             */

            client.getSubscriptionStatus();
        }
    );

    /* ideally we could get detailed subscription info via DBus, but we
     * can't rely on this being present on all systems we work on
     */
    legacyService.subscribe(
        { path: "/EntitlementStatus",
          interface: "org.freedesktop.DBUS.Properties",
          member: "PropertiesChanged"
        },
        () => {
            client.getSubscriptionStatus();
        }
    );

    // get initial status
    requestUpdate();
    // read config (async)
    client.readConfig().then(needRender);
};

module.exports = client;
