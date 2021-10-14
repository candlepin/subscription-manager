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

var cockpit = require("cockpit");
var _ = cockpit.gettext;

var React = require("react");
import 'form-layout.scss';

import { FormSelect, FormSelectOption } from '@patternfly/react-core';

import subscriptionsClient from './subscriptions-client';
import * as Insights from './insights.jsx';

/* Subscriptions: registration dialog body
 * Expected props:
 *   - onChange  callback to signal when the data has changed
 *   - properties as in defaultRegisterDialogSettings()
 */
class SubscriptionRegisterDialog extends React.Component {
    render() {
        let customURL;
        if (this.props.url === 'custom') {
            customURL = (
                <input id="subscription-register-url-custom" className="form-control" type="text"
                 value={this.props.server_url} onChange={value => this.props.onChange('server_url', value)} />
            );
        }
        let proxy;
        if (this.props.proxy) {
            proxy = (
                <div className="proxy-settings-form">
                    <form className="ct-form-layout" id="subscription-register-proxy-form">
                        <label className="control-label" htmlFor="subscription-proxy-server">
                            {_("Proxy Location")}
                        </label>
                        <input className="form-control" id="subscription-proxy-server" type="text"
                               placeholder="hostname:port" value={this.props.proxy_server}
                               onChange={value => this.props.onChange('proxy_server', value)} />

                        <label className="control-label" htmlFor="subscription-proxy-user">
                            {_("Proxy Username")}
                        </label>
                        <input className="form-control" id="subscription-proxy-user" type="text"
                               value={this.props.proxy_user}
                               onChange={value => this.props.onChange('proxy_user', value)} />

                        <label className="control-label" htmlFor="subscription-proxy-password">
                            {_("Proxy Password")}
                        </label>
                        <input className="form-control" id="subscription-proxy-password" type="password"
                               value={this.props.proxy_password}
                               onChange={value => this.props.onChange('proxy_password', value)} />
                    </form>
                </div>
            );
        }
        let insights;
        let insights_checkbox_disabled = true;
        if (this.props.insights_available === true) {
            insights_checkbox_disabled = false;
        } else {
            if (this.props.auto_attach === true) {
                insights_checkbox_disabled = false;
            }
        }
        insights = [
            <label key="0" className="control-label" htmlFor="subscription-insights">
                {_("Insights")}
            </label>,
            <label key="1" className="checkbox-inline">
                <input id="subscription-insights" type="checkbox" checked={this.props.insights}
                       disabled={ insights_checkbox_disabled } onChange={value => this.props.onChange('insights', value)} />
                <span>
                    { Insights.arrfmt(_("Connect this system to $0."), Insights.link) }
                </span>
            </label>,
            (this.props.insights && !this.props.insights_detected) && <p>{ Insights.arrfmt(_("The $0 package will be installed."), <strong>{subscriptionsClient.insightsPackage}</strong>)}</p>
        ];


        let credentials;
        if (this.props.register_method === "account") {
            credentials = (
                <div className="ct-form-layout" id="subscription-credentials">
                    <label className="control-label" htmlFor="subscription-register-username">
                        {_("Username")}
                    </label>
                    <input id="subscription-register-username" className="form-control" type="text"
                           value={this.props.user}
                           onChange={value => this.props.onChange('user', value)} />
                    <label className="control-label" htmlFor="subscription-register-password">
                        {_("Password")}
                    </label>
                    <input id="subscription-register-password" className="form-control" type="password"
                           value={this.props.password}
                           onChange={value => this.props.onChange('password', value)} />
                    <label className="control-label" htmlFor="subscription-register-org">
                        {_("Organization")}
                    </label>
                    <input id="subscription-register-org" className="form-control" type="text"
                           value={this.props.org}
                           onChange={value => this.props.onChange('org', value)} />
                </div>
            );
        } else {
            credentials = (
                <div className="ct-form-layout" id="subscription-credentials">
                    <label className="control-label" htmlFor="subscription-register-key">
                        {_("Activation Key")}
                    </label>
                    <input id="subscription-register-key" className="form-control" type="text"
                        placeholder="key_one,key_two" value={this.props.activation_keys}
                        onChange={value => this.props.onChange('activation_keys', value)} />
                    <label className="control-label" htmlFor="subscription-register-org">
                        {_("Organization")}
                    </label>
                    <input id="subscription-register-org" className="form-control" type="text"
                           value={this.props.org}
                           onChange={value => this.props.onChange('org', value)} />
                </div>
            );
        }

        const urlEntries = {
            'default': _("Default"),
            'custom': _("Custom URL"),
        };
        return (
            <div className="modal-body">
                <form className="ct-form-layout">
                    <label className="control-label" htmlFor="subscription-register-url">
                        {_("URL")}
                    </label>
                    <FormSelect key='urlSource' onChange={value => this.props.onChange('url', value)}
                            id="subscription-register-url" value={this.props.url}>
                        <FormSelectOption value="default" label={urlEntries['default']} />
                        <FormSelectOption value="custom" label={urlEntries['custom']} />
                    </FormSelect>
                    {customURL}
                    <label className="checkbox-inline">
                        <input id="subscription-proxy-use" type="checkbox" checked={this.props.proxy}
                               onChange={value => this.props.onChange('proxy', value)} />
                        {_("Use proxy server")}
                    </label>
                    {proxy}
                    <label className="control-label" htmlFor="subscription-register-method">
                        {_("Method")}
                    </label>
                    <label className="checkbox-inline">
                        <div className="rhsm-register-method">
                            <label id="account-method-label">
                                <input id="subscription-register-account-method" type="radio"
                                       name="subscription-register-account-method"
                                       radioGroup="subscription-register-method" value="account"
                                       onChange={value => this.props.onChange('register_method', value)}
                                       checked={this.props.register_method === 'account'}
                                />
                                <span className="register-method-value">{_("Account")}</span>
                            </label>
                            <label id="activation-key-method-label">
                                <input id="subscription-register-activation-key-method" type="radio"
                                       name="subscription-register-activation-key-method"
                                       radioGroup="subscription-register-method" value="activation-key"
                                       onChange={value => this.props.onChange('register_method', value)}
                                       checked={this.props.register_method === 'activation-key'}
                                />
                                <span className="register-method-value">{_("Activation key")}</span>
                            </label>
                        </div>
                    </label>
                    { credentials }
                    <label className="control-label">
                        {_("Subscriptions")}
                    </label>
                    <label className="checkbox-inline">
                        <input id="subscription-auto-attach-use" type="checkbox" checked={this.props.auto_attach}
                               onChange={value => this.props.onChange('auto_attach', value)}
                        />
                        {_("Attach automatically")}
                    </label>
                    { insights }
                </form>
            </div>
        );
    }
}

export default SubscriptionRegisterDialog;
