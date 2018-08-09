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

import cockpit from 'cockpit';
import React from 'react';
import subscriptionsClient from './subscriptions-client';
import { ListView, ListViewItem, ListViewIcon } from 'patternfly-react';
import { Row, Col } from 'react-bootstrap';

let _ = cockpit.gettext;

class Listing extends React.Component {
    render() {
        if (this.props.children) {
            return (
                <div>
                    <h2>{this.props.title}</h2>
                    {this.props.children}
                </div>
            );
        } else {
            return (
                <div>
                    <h2>{this.props.emptyCaption}</h2>
                </div>
            );
        }
    }
}

/* 'Curtains' implements a subset of the PatternFly Empty State pattern
 * https://www.patternfly.org/patterns/empty-state/
 * Special values for icon property:
 *   - 'waiting' - display spinner
 *   - 'error'   - display error icon
 */
class Curtains extends React.Component {
    render() {
        let description = null;
        if (this.props.description)
            description = <h1>{this.props.description}</h1>;

        let message = null;
        if (this.props.message)
            message = <p>{this.props.message}</p>;

        let curtains = "curtains-ct";

        let icon = this.props.icon;
        if (icon === 'waiting')
            icon = <div className="spinner spinner-lg"/>;
        else if (icon === 'error')
            icon = <div className="pficon pficon-error-circle-o"/>;

        return (
            <div className={ curtains + " blank-slate-pf" }>
                <div className="blank-slate-pf-icon">
                    {icon}
                </div>
                {description}
                {message}
            </div>
        );
    }
}

/* Component to show a dismissable error, message as child text
 * dismissError callback function triggered when the close button is pressed
 */
class DismissableError extends React.Component {
    handleDismissError(err) {
        // only consider primary mouse button
        if (!err || err.button !== 0)
            return;
        if (this.props.dismissError)
            this.props.dismissError();
        err.stopPropagation();
    }
    render() {
        return (
            <div className="alert alert-danger alert-dismissable alert-ct-top">
                <span className="pficon pficon-error-circle-o" />
                <span>{this.props.children}</span>
                <button type="button" className="close" aria-hidden="true" onClick={this.handleDismissError}>
                    <span className="pficon pficon-close"/>
                </button>
            </div>
        );
    }
}

/* Show subscriptions status of the system, offer to register/unregister the system
 * Expected properties:
 * status       subscription status
 * error        error message to show (in Curtains if not connected, as a dismissable alert otherwise
 * dismissError callback, triggered for the dismissable error in connected state
 * register     callback, triggered when user clicks on register
 * unregister   callback, triggered when user clicks on unregister
 */
class SubscriptionStatus extends React.Component {
    constructor(props) {
        super(props);
        // React components using ES6 classes no longer autobind this to non React
        // methods.
        this.handleRegisterSystem = this.handleRegisterSystem.bind(this);
        this.handleUnregisterSystem = this.handleUnregisterSystem.bind(this);
    }
    handleRegisterSystem(err) {
        // only consider primary mouse button
        if (!err || err.button !== 0)
            return;
        if (this.props.register)
            this.props.register();
        err.stopPropagation();
    }
    handleUnregisterSystem(e) {
        // only consider primary mouse button
        if (!e || e.button !== 0)
            return;
        if (this.props.unregister)
            this.props.unregister();
        e.stopPropagation();
    }
    render() {
        let errorMessage;
        if (this.props.error) {
            errorMessage = (
                <DismissableError dismissError={this.props.dismissError}>{String(this.props.error)}</DismissableError>
            );
        }

        let label;
        let action;
        let note;
        let syspurpose;
        let sla;
        let usage;
        let role;
        let add_ons;
        let syspurpose_status;
        let isUnregistering = (this.props.status === "unregistering");
        if (this.props.syspurpose["service_level_agreement"]) {
            sla = (
                <div>
                    <label>
                        { _("Service Level:  ") }
                        { _(String(this.props.syspurpose["service_level_agreement"])) }
                    </label>
                </div>
            );
        }
        if (this.props.syspurpose["usage"]) {
            usage = (
                <div>
                    <label>
                        { _("Usage:  ") }
                        { _(String(this.props.syspurpose["usage"])) }
                    </label>
                </div>
        );
        }
        if (this.props.syspurpose["role"]) {
            role = (
                <div>
                    <label>
                        { _("Role:  ") }
                        { _(String(this.props.syspurpose["role"])) }
                    </label>
                </div>
            );
        }
        if (this.props.syspurpose["addons"]) {
            add_ons = (
                <div>
                    <label>
                        { _("Addons:  ") }
                        { _(String(subscriptionsClient.toArray(this.props.syspurpose["addons"]).join(", "))) }
                    </label>
                </div>
            );
        }
        if (this.props.syspurpose_status) {
            syspurpose_status = (
                <div>
                    <label>
                        { _("Status: ") }
                        { _(String(this.props.syspurpose_status)) }
                    </label>
                </div>
            );
        }
        syspurpose = (
            <div>
                <h2>{_("System Purpose")}</h2>
                <div className="dl-horizontal">
                    {syspurpose_status}
                    {sla}
                    {usage}
                    {role}
                    {add_ons}
                </div>
            </div>
        );
        if (this.props.status === 'Unknown') {
            label = <label>{ `${_("Status")}: ${_("This system is currently not registered.")}` }</label>;
            action = (<button className="btn btn-primary"
                              onClick={this.handleRegisterSystem}>{_("Register")}</button>
            );
        } else {
            label = <label>{ `${_("Status")}: ${this.props.status}` }</label>;
            action = (<button className="btn btn-primary" disabled={isUnregistering}
                              onClick={this.handleUnregisterSystem}>{_("Unregister")}</button>
            );
            if (isUnregistering) {
                note = (
                    <div className="dialog-wait-ct">
                        <div className="spinner spinner-sm"/>
                        <span>{ _("Unregistering") }</span>
                    </div>
                );
            }
        }
        return (
            <div className="subscription-status-ct">
                <h2>{_("Subscriptions")}</h2>
                {errorMessage}
                {label}
                {action}
                {syspurpose}
                {note}
            </div>
        );
    }
}

/* Show subscriptions status of the system and registered products, offer to register/unregister the system
 * Expected properties:
 * status       subscription status
 * error        error message to show (in Curtains if not connected, as a dismissable alert otherwise
 * dismissError callback, triggered for the dismissable error in connected state
 * products     subscribed products (properties as in subscriptions-client)
 * register     callback, triggered when user clicks on register
 * unregister   callback, triggered when user clicks on unregister
 */
class SubscriptionsPage extends React.Component {
    renderCurtains() {
        let icon;
        let description;
        let message;
        if (this.props.status === "service-unavailable") {
            icon = <div className="fa fa-exclamation-circle"/>;
            message = _("The rhsm service is unavailable. Make sure subscription-manager is installed " +
                "and try reloading the page. Additionally, make sure that you have checked the " +
                "'Reuse my password for privileged tasks' checkbox on the login page.");
            description = _("Unable to the reach the rhsm service.");
        } else if (this.props.status === undefined || !subscriptionsClient.config.loaded) {
            icon = <div className="spinner spinner-lg" />;
            message = _("Updating");
            description = _("Retrieving subscription status...");
        } else if (this.props.status === 'access-denied') {
            icon = <div className="fa fa-exclamation-circle" />;
            message = _("Access denied");
            description = _("The current user isn't allowed to access system subscription status.");
        } else {
            icon = <div className="fa fa-exclamation-circle" />;
            message = _("Unable to connect");
            description = _("Couldn't get system subscription status. Please ensure subscription-manager is installed.");
        }
        return (
            <Curtains
                icon={icon}
                description={description}
                message={message} />
        );
    }
    renderSubscriptions() {
        let entries = this.props.products.map(function (itm) {
            let icon_name;
            let status_text;

            if (itm.status === 'subscribed') {
                icon_name = "fa pficon-ok";
            } else {
                icon_name = "fa pficon-error-circle-o";
            }

            if (itm.status === 'subscribed') {
                status_text = _("Subscribed");
            } else {
                status_text = _("Not Subscribed (Not supported by a valid subscription.)");
            }

            return (
                <ListViewItem
                    leftContent={<ListViewIcon icon={ icon_name } />}
                    heading={ itm.productName }
                    key={itm.productId}
                >
                    <Row>
                        <Col sm={11}>
                            <div className="col-md-11">
                                <dl className="dl-horizontal">
                                    <dt>{ _("Product Name") }</dt>
                                    <dd>{ itm.productName }</dd>
                                    <dt>{ _("Product ID") }</dt>
                                    <dd>{ itm.productId }</dd>
                                    <dt>{ _("Version") }</dt>
                                    <dd>{ itm.version }</dd>
                                    <dt>{ _("Arch") }</dt>
                                    <dd>{ itm.arch }</dd>
                                    <dt>{ _("Status") }</dt>
                                    <dd>{ status_text }</dd>
                                    <dt>{ _("Starts") }</dt>
                                    <dd>{ itm.starts }</dd>
                                    <dt>{ _("Ends") }</dt>
                                    <dd>{ itm.ends }</dd>
                                </dl>
                            </div>
                        </Col>
                    </Row>
                </ListViewItem>
            );
        });

        return (
            <div className="container-fluid">
            <SubscriptionStatus {...this.props }/>
            <Listing
                    title={ _("Installed products") }
                    emptyCaption={ _("No installed products detected.") }
                    >
                <ListView className="installed-products">
                {entries}
                </ListView>
            </Listing>
            </div>
        );
    }
    render() {
        if (this.props.status === undefined ||
            this.props.status === 'not-found' ||
            this.props.status === 'access-denied' ||
            !subscriptionsClient.config.loaded) {
            return this.renderCurtains();
        } else {
            return this.renderSubscriptions();
        }
    }
}

module.exports = {
    page: SubscriptionsPage,
};
