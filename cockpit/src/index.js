/*
 * This file is part of Cockpit.
 *
 * Copyright (C) 2015 Red Hat, Inc.
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

import cockpit from 'cockpit';
import React from 'react';
import ReactDOM from 'react-dom';

import '../lib/patternfly/patternfly-cockpit.scss';

import subscriptionsClient from './subscriptions-client';
import SubscriptionRegisterDialog from './subscriptions-register.jsx';
import SubscriptionsView from './subscriptions-view.jsx';
import * as Insights from './insights.jsx';
import * as Dialog from '../lib/cockpit-components-dialog.jsx';

import './subscriptions.scss';

let _ = cockpit.gettext;

let dataStore = { };

let registerDialogDetails = {
    user: '',
    password: '',
    activation_keys: '',
    org: '',
    proxy_server: '',
    proxy_user: '',
    proxy_password: '',
    insights: false
};

function dismissStatusError() {
    subscriptionsClient.subscriptionStatus.error = undefined;
    dataStore.render();
}

function registerSystem (update_progress) {
    return subscriptionsClient.registerSystem(registerDialogDetails, update_progress).then(() => {
        if (registerDialogDetails.insights)
            return Insights.register(update_progress).catch(Insights.catch_error);
    });
}

let footerProps = {
    'actions': [
        { 'clicked': registerSystem,
          'caption': _("Register"),
          'style': 'primary',
        },
    ]
};

function openRegisterDialog() {
    // Read configuration file before opening register dialog
    subscriptionsClient.readConfig().then(() => {
        // set config to what was loaded and clean previous credential information
        Object.assign(registerDialogDetails, subscriptionsClient.config, {
            user: '',
            password: '',
            activation_keys: '',
            org: '',
            insights: false,
            insights_available: subscriptionsClient.insightsAvailable,
            insights_detected: false,
            register_method: 'account',
            auto_attach: true
        });

        Insights.detect().then(installed => {
            registerDialogDetails.insights_detected = installed;

            // show dialog to register
            let renderDialog;
            let updatedData = function(prop, data) {
                if (prop) {
                    if (data.target) {
                        if (data.target.type === "checkbox") {
                            registerDialogDetails[prop] = data.target.checked;
                        } else {
                            registerDialogDetails[prop] = data.target.value;
                        }
                    } else {
                        registerDialogDetails[prop] = data;
                    }
                }

                registerDialogDetails.onChange = updatedData;

                let dialogProps = {
                    'id': 'register_dialog',
                    'title': _("Register System"),
                    'body': React.createElement(SubscriptionRegisterDialog, registerDialogDetails),
                };

                if (renderDialog)
                    renderDialog.setProps(dialogProps);
                else
                    renderDialog = Dialog.show_modal_dialog(dialogProps, footerProps);
            };
            updatedData();
        });
    });
}

function unregisterSystem() {
    Insights.unregister().catch(() => true).then(subscriptionsClient.unregisterSystem);
}

function initStore(rootElement) {
    subscriptionsClient.addEventListener("dataChanged",
                                         () => {
                                             dataStore.render();
                                         }
    );

    dataStore.render = () => {
        ReactDOM.render(React.createElement(
            SubscriptionsView,
            {
                status: subscriptionsClient.subscriptionStatus.status,
                status_msg: subscriptionsClient.subscriptionStatus.status_msg,
                products:subscriptionsClient.subscriptionStatus.products,
                error: subscriptionsClient.subscriptionStatus.error,
                syspurpose: subscriptionsClient.syspurposeStatus.info,
                syspurpose_status: subscriptionsClient.syspurposeStatus.status,
                insights_available: subscriptionsClient.insightsAvailable,
                autoAttach: subscriptionsClient.autoAttach,
                dismissError: dismissStatusError,
                register: openRegisterDialog,
                unregister: unregisterSystem,
            }),
                        rootElement
        );
    };
    subscriptionsClient.init();
}

document.addEventListener("DOMContentLoaded", function() {
    initStore(document.getElementById('app'));
    dataStore.render();
});
