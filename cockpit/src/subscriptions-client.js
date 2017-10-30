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
            /* TODO start date and end date */
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

    if (subscriptionDetails.url != 'default') {
        /*  parse url into host, port, handler; sorry about the ugly regex
            (?:https?://)? strips off the protocol if it exists
            ([$/:]+) matches the hostname
            (?::(?=[0-9])([0-9]+))? matches the port if it exists
            (?:(/.+)) matches the rest for the path
        */
        const pattern = new RegExp('^(?:https?://)?([^/:]+)(?::(?=[0-9])([0-9]+))?(?:(/.+))?$');
        const match = pattern.exec(subscriptionDetails.serverUrl); // TODO handle failure
        connection_options.host = {
            t: 's',
            v: match[1],
        };
        if (match[2]) {
            connection_options.port = {
                t: 's',
                v: match[2],
            };
        }
        if (match[3]) {
            connection_options.handler = {
                t: 's',
                v: match[3],
            };
        }
    }

    // proxy is optional
    if (subscriptionDetails.proxy) {
        if (subscriptionDetails.proxyServer) {
            const pattern = new RegExp('^([^:]*):?(.*)$');
            const match = pattern.exec(subscriptionDetails.proxyServer);
            if (match[1]) {
                connection_options.proxy_hostname = {
                    t: 's',
                    v: match[1],
                };
            }
            if (match[2]) {
                connection_options.proxy_port = {
                    t: 's',
                    v: match[2],
                }
            }
        }
        if (subscriptionDetails.proxyUser) {
            connection_options.proxy_user = {
                t: 's',
                v: subscriptionDetails.proxyUser,
            };
        }
        if (subscriptionDetails.proxyPassword) {
            connection_options.proxy_password = {
                t: 's',
                v: subscriptionDetails.proxyPassword,
            };
        }
    }

    console.debug('connection_options:', connection_options);

    registerServer.wait(() => {
        registerServer.Start()
            .then(socket => {
                console.debug('Opening private bus interface at ' + socket);
                const private_interface = cockpit.dbus(null, {bus: 'none', address: socket, superuser: 'require'});
                const registerService = private_interface.proxy('com.redhat.RHSM1.Register', '/com/redhat/RHSM1/Register');
                if (subscriptionDetails.activationKeys) {
                    return registerService.call('RegisterWithActivationKeys', [subscriptionDetails.org, subscriptionDetails.activationKeys.split(','), {}, connection_options]);
                }
                else {
                    return registerService.call('Register', [subscriptionDetails.org, subscriptionDetails.user, subscriptionDetails.password, {}, connection_options]);
                }
            })
            .catch(error => {
                console.error('error registering', error);
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
                console.debug('auto-attaching');
                return attachService.AutoAttach('', {});
            })
            .catch(error => {
                console.error('error during autoattach', error);
                dfd.reject(error);
            })
            .then(() => {
                console.debug('requesting update');
                requestUpdate();
                dfd.resolve();
            });
    });

    var promise = dfd.promise();
    return promise;
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
};

module.exports = client;
