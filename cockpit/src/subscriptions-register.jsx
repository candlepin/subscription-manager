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
import Select from "./Select/Select.jsx";
import '../lib/form-layout.less';

/* Subscriptions: registration dialog body
 * Expected props:
 *   - onChange  callback to signal when the data has changed
 *   - properties as in defaultRegisterDialogSettings()
 */
class PatternDialogBody extends React.Component {
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
                <form className="ct-form-layout">
                    <label className="control-label" htmlFor="subscription-proxy-server">
                        {_("Proxy Location")}
                    </label>
                    <input className="form-control" id="subscription-proxy-server" type="text"
                           placeholder="hostname:port" value={this.props.proxy_server}
                           onChange={value => this.props.onChange('proxy_server', value)}/>

                    <label className="control-label" htmlFor="subscription-proxy-user">
                        {_("Proxy Username")}
                    </label>
                    <input className="form-control" id="subscription-proxy-user" type="text"
                           value={this.props.proxy_user}
                           onChange={value => this.props.onChange('proxy_user', value)}/>

                    <label className="control-label" htmlFor="subscription-proxy-password">
                        {_("Proxy Password")}
                    </label>
                    <input className="form-control" id="subscription-proxy-password" type="password"
                           value={this.props.proxy_password}
                           onChange={value => this.props.onChange('proxy_password', value)}/>
                </form>
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
                    <Select key='urlSource' onChange={value => this.props.onChange('url', value)}
                            id="subscription-register-url" value={this.props.url}>
                        <option value="default">{ urlEntries['default'] }</option>
                        <option value="custom" >{ urlEntries['custom'] }</option>
                    </Select>
                    {customURL}
                    <label className="control-label">
                        {_("Proxy")}
                    </label>
                    <label className="checkbox-inline">
                        <input id="subscription-proxy-use" type="checkbox" checked={this.props.proxy}
                               onChange={value => this.props.onChange('proxy', value)}/>
                        {_("I would like to connect via an HTTP proxy.")}
                    </label>
                    {proxy}
                    <label className="control-label" htmlFor="subscription-register-username">
                        {_("Login")}
                    </label>
                    <input id="subscription-register-username" className="form-control" type="text"
                           value={this.props.user}
                           onChange={value => this.props.onChange('user', value)}/>
                    <label className="control-label" htmlFor="subscription-register-password">
                        {_("Password")}
                    </label>
                    <input id="subscription-register-password" className="form-control" type="password"
                           value={this.props.password}
                           onChange={value => this.props.onChange('password', value)}/>
                    <label className="control-label" htmlFor="subscription-register-key">
                        {_("Activation Key")}
                    </label>
                    <input id="subscription-register-key" className="form-control" type="text"
                           placeholder="key_one,key_two" value={this.props.activation_keys}
                           onChange={value => this.props.onChange('activation_keys', value)}/>

                    <label className="control-label" htmlFor="subscription-register-org">
                        {_("Organization")}
                    </label>
                    <input id="subscription-register-org" className="form-control" type="text"
                           value={this.props.org}
                           onChange={value => this.props.onChange('org', value)}/>
                </form>
            </div>
        );
    }
}

module.exports = {
    dialogBody: PatternDialogBody,
};
