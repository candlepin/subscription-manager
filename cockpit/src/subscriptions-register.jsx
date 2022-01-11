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

import {
    Checkbox,
    Flex,
    Form, FormGroup,
    FormSelect, FormSelectOption,
    Radio,
    TextInput,
} from '@patternfly/react-core';

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
                <TextInput id="subscription-register-url-custom"
                           value={this.props.server_url} onChange={value => this.props.onChange('server_url', value)} />
            );
        }
        let proxy;
        if (this.props.proxy) {
            proxy = (
                <>
                    <FormGroup fieldId="subscription-proxy-server" label={_("Proxy Location")}>
                        <TextInput id="subscription-proxy-server"
                                    placeholder="hostname:port" value={this.props.proxy_server}
                                    onChange={value => this.props.onChange('proxy_server', value)} />
                    </FormGroup>

                    <FormGroup fieldId="subscription-proxy-user" label={_("Proxy Username")}>
                        <TextInput id="subscription-proxy-user"
                                   value={this.props.proxy_user}
                                   onChange={value => this.props.onChange('proxy_user', value)} />
                    </FormGroup>

                    <FormGroup fieldId="subscription-proxy-password" label={_("Proxy Password")}>
                        <TextInput id="subscription-proxy-password" type="password"
                                   value={this.props.proxy_password}
                                   onChange={value => this.props.onChange('proxy_password', value)} />
                    </FormGroup>
                </>
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
            <FormGroup key="0" fieldId="subscription-insights" label={_("Insights")} hasNoPaddingTop>
                <Checkbox id="subscription-insights" isChecked={this.props.insights}
                          label={ Insights.arrfmt(_("Connect this system to $0."), Insights.link) }
                          isDisabled={ insights_checkbox_disabled }
                          onChange={value => this.props.onChange('insights', value)}
                />
                {(this.props.insights && !this.props.insights_detected) &&
                    <p>
                        { Insights.arrfmt(
                            _("The $0 package will be installed."),
                            <strong>{subscriptionsClient.insightsPackage}</strong>
                        )}
                    </p>
                }
            </FormGroup>,
        ];


        let credentials;
        if (this.props.register_method === "account") {
            credentials = (
                <>
                    <FormGroup fieldId="subscription-register-username" label={_("Username")}>
                        <TextInput id="subscription-register-username"
                                   value={this.props.user}
                                   onChange={value => this.props.onChange('user', value)} />
                    </FormGroup>
                    <FormGroup fieldId="subscription-register-password" label={_("Password")}>
                        <TextInput id="subscription-register-password" type="password"
                                   value={this.props.password}
                                   onChange={value => this.props.onChange('password', value)} />
                    </FormGroup>
                    <FormGroup fieldId="subscription-register-org" label={_("Organization")}>
                        <TextInput id="subscription-register-org"
                                   value={this.props.org}
                                   onChange={value => this.props.onChange('org', value)} />
                    </FormGroup>
                </>
            );
        } else {
            credentials = (
                <>
                    <FormGroup fieldId="subscription-register-key" label={_("Activation Key")}>
                        <TextInput id="subscription-register-key"
                                   placeholder="key_one,key_two" value={this.props.activation_keys}
                                   onChange={value => this.props.onChange('activation_keys', value)} />
                    </FormGroup>
                    <FormGroup fieldId="subscription-register-org" label={_("Organization")}>
                        <TextInput id="subscription-register-org"
                                   value={this.props.org}
                                   onChange={value => this.props.onChange('org', value)} />
                    </FormGroup>
                </>
            );
        }

        const urlEntries = {
            'default': _("Default"),
            'custom': _("Custom URL"),
        };
        return (
            <Form isHorizontal>
                <FormGroup fieldId="subscription-register-url" label={_("URL")} isStack>
                    <FormSelect key='urlSource' onChange={value => this.props.onChange('url', value)}
                            id="subscription-register-url" value={this.props.url}>
                        <FormSelectOption value="default" label={urlEntries['default']} />
                        <FormSelectOption value="custom" label={urlEntries['custom']} />
                    </FormSelect>
                    {customURL}
                    <Checkbox id="subscription-proxy-use" isChecked={this.props.proxy}
                              label={_("Use proxy server")}
                              onChange={value => this.props.onChange('proxy', value)} />
                    {proxy}
                </FormGroup>
                <FormGroup fieldId="subscription-register-method" label={_("Method")} isStack hasNoPaddingTop>
                    <Flex>
                        <Radio id="subscription-register-account-method"
                               name="subscription-register-account-method"
                               label={_("Account")}
                               onChange={() => this.props.onChange('register_method', 'account')}
                               isChecked={this.props.register_method === 'account'} />
                        <Radio id="subscription-register-activation-key-method"
                               name="subscription-register-activation-key-method"
                               label={_("Activation key")}
                               onChange={() => this.props.onChange('register_method', 'activation-key')}
                               isChecked={this.props.register_method === 'activation-key'} />
                    </Flex>
                    { credentials }
                </FormGroup>
                <FormGroup className="control-label" label={_("Subscriptions")} hasNoPaddingTop>
                    <Checkbox id="subscription-auto-attach-use" isChecked={this.props.auto_attach}
                              label={_("Attach automatically")}
                              onChange={value => {
                                  this.props.onChange('auto_attach', value);
                                  this.props.insights && !value && this.props.onChange('insights', value);
                              }}
                    />
                </FormGroup>
                { insights }
            </Form>
        );
    }
}

export default SubscriptionRegisterDialog;
