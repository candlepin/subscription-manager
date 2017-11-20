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

/* Subscriptions: registration dialog body
 * Expected props:
 *   - onChange  callback to signal when the data has changed
 *   - properties as in defaultRegisterDialogSettings()
 */
var PatternDialogBody = React.createClass({
    render: function() {
        var customURL;
        if (this.props.url == 'custom') {
            customURL = (
                <input id="subscription-register-url-custom" className="form-control" type="text"
                 value={this.props.serverUrl} onChange={value => this.props.onChange('serverUrl', value)} />
            );
        }
        var proxy;
        if (this.props.proxy) {
            proxy = [
                <br />,
                <table className="form-group-ct">
                    <tbody>
                        <tr>
                            <td>
                                <label className="control-label" htmlFor="subscription-proxy-server">
                                    {_("Proxy Location")}
                                </label>
                            </td>
                            <td><input className="form-control" id="subscription-proxy-server" type="text"
                                       placeholder="hostname:port" value={this.props.proxyServer}
                                       onChange={value => this.props.onChange('proxyServer', value)}/>
                            </td>
                        </tr>

                        <tr>
                            <td>
                                <label className="control-label" htmlFor="subscription-proxy-user">
                                    {_("Proxy Username")}
                                </label>
                            </td>
                            <td><input className="form-control" id="subscription-proxy-user" type="text"
                                       value={this.props.proxyUser}
                                       onChange={value => this.props.onChange('proxyUser', value)}/>
                            </td>
                        </tr>

                        <tr>
                            <td>
                                <label className="control-label" htmlFor="subscription-proxy-password">
                                    {_("Proxy Password")}
                                </label>
                            </td>
                            <td><input className="form-control" id="subscription-proxy-password" type="password"
                                       value={this.props.proxyPassword}
                                       onChange={value => this.props.onChange('proxyPassword', value)}/>
                            </td>
                        </tr>
                    </tbody>
                </table>
            ];
        }
        var urlEntries = {
            'default': _("Default"),
            'custom': _("Custom URL"),
        };
        return (
            <div className="modal-body">
                <table className="form-table-ct">
                    <tbody>
                        <tr>
                            <td className="top">
                                <label className="control-label" htmlFor="subscription-register-url">
                                    {_("URL")}
                                </label>
                            </td>
                            <td>
                                <Select key='urlSource' onChange={value => this.props.onChange('url', value)}
                                        id="subscription-register-url" value={this.props.url}>
                                    <option value="default">{ urlEntries['default'] }</option>
                                    <option value="custom" >{ urlEntries['custom'] }</option>
                                </Select>
                                {customURL}
                            </td>
                        </tr>
                        <tr>
                            <td className="top">
                                <label className="control-label">
                                    {_("Proxy")}
                                </label>
                            </td>
                            <td>
                                <label>
                                    <input id="subscription-proxy-use" type="checkbox" checked={this.props.proxy}
                                           onChange={value => this.props.onChange('proxy', value)}/>
                                    {_("I would like to connect via an HTTP proxy.")}
                                </label>
                                {proxy}
                            </td>
                        </tr>
                        <tr>
                            <td className="top ">
                                <label className="control-label" htmlFor="subscription-register-username">
                                    {_("Login")}
                                </label>
                            </td>
                            <td>
                                <input id="subscription-register-username" className="form-control" type="text"
                                       value={this.props.user}
                                       onChange={value => this.props.onChange('user', value)}/>
                            </td>
                        </tr>
                        <tr>
                            <td className="top">
                                <label className="control-label" htmlFor="subscription-register-password">
                                    {_("Password")}
                                </label>
                            </td>
                            <td>
                                <input id="subscription-register-password" className="form-control" type="password"
                                       value={this.props.password}
                                       onChange={value => this.props.onChange('password', value)}/>
                            </td>
                        </tr>
                        <tr>
                            <td className="top">
                                <label className="control-label" htmlFor="subscription-register-key">
                                    {_("Activation Key")}
                                </label>
                            </td>
                            <td>
                                <input id="subscription-register-key" className="form-control" type="text"
                                       placeholder="key_one,key_two" value={this.props.activationKeys}
                                       onChange={value => this.props.onChange('activationKeys', value)}/>
                            </td>
                        </tr>
                        <tr>
                            <td className="top">
                                <label className="control-label" htmlFor="subscription-register-org">
                                    {_("Organization")}
                                </label>
                            </td>
                            <td>
                                <input id="subscription-register-org" className="form-control" type="text"
                                       value={this.props.org}
                                       onChange={value => this.props.onChange('org', value)}/>
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
        );
    }
});

module.exports = {
    dialogBody: PatternDialogBody,
};
