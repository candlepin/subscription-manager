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
import createFragment from 'react-addons-create-fragment';
import subscriptionsClient from './subscriptions-client';
import { ListView, ListViewItem, ListViewIcon } from 'patternfly-react';
import { Button } from "react-bootstrap";
import { Row, Col } from 'react-bootstrap';
import { InsightsStatus } from './insights.jsx';

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
    constructor(props) {
        super(props);
        // This binding is necessary to make `this` work in the callback
        this.handleDismissError = this.handleDismissError.bind(this);
    }
    handleDismissError(err) {
        // only consider primary mouse button
        if (!err || err.button !== 0)
            return;
        if (this.props.dismissError) {
            this.props.dismissError();
        }
        err.stopPropagation();
    }
    render() {
        let debug_str = JSON.stringify(this.props.children);
        console.debug(debug_str);
        let classes_div = "alert alert-danger alert-dismissable alert-ct-top";
        let classes_icon = "pficon pficon-error-circle-o";

        console.debug(this.props.children.severity);

        if (this.props.children[0] === "error") {
            classes_div = "alert alert-danger alert-dismissable alert-ct-top";
            classes_icon = "pficon pficon-error-circle-o";
        }
        if (this.props.children[0] === "warning") {
            classes_div = "alert alert-warning alert-dismissable alert-ct-top";
            classes_icon = "pficon pficon-warning-triangle-o"
        }
        if (this.props.children[0] === "info") {
            classes_div = "alert alert-info alert-dismissable alert-ct-top";
            classes_icon = "pficon pficon-info"
        }

        return (
            <div className={classes_div}>
                <span className={classes_icon} />
                <span>{this.props.children[1]}</span>
                <button type="button" className="close" aria-hidden="true" onClick={this.handleDismissError}>
                    <span className="pficon pficon-close"/>
                </button>
            </div>
        );
    }
}

class SystemPurposeStatusCard extends React.Component {
    constructor(props) {
        super(props);
    }
    render() {
        let sla;
        let usage;
        let role;
        let add_ons;
        let syspurpose_status;
        if (this.props.syspurpose["service_level_agreement"]) {
            sla = (
                <div>
                    <label>
                        { _("Service Level:  ") }
                        <span className="value">{ _(String(this.props.syspurpose["service_level_agreement"])) }</span>
                    </label>
                </div>
            );
        }
        if (this.props.syspurpose["usage"]) {
            usage = (
                <div>
                    <label>
                        { _("Usage:  ") }
                        <span className="value">{ _(String(this.props.syspurpose["usage"])) }</span>
                    </label>
                </div>
        );
        }
        if (this.props.syspurpose["role"]) {
            role = (
                <div>
                    <label>
                        { _("Role:  ") }
                        <span className="value">{ _(String(this.props.syspurpose["role"])) }</span>
                    </label>
                </div>
            );
        }
        if (this.props.syspurpose["addons"]) {
            add_ons = (
                <div>
                    <label>
                        { _("Addons:  ") }
                        <span className="value">
                            { _(String(subscriptionsClient.toArray(this.props.syspurpose["addons"]).join(", "))) }
                        </span>
                    </label>
                </div>
            );
        }
        if (this.props.syspurpose_status) {
            syspurpose_status = (
                <div>
                    <label>
                        { _("Status: ") }
                        <span className="value">{ _(String(this.props.syspurpose_status)) }</span>
                    </label>
                </div>
            );
        }
        return (
            <div className="card-pf">
                <div className="card-pf-heading">
                    <h2 className="card-pf-title">
                        { _("System Purpose") }
                    </h2>
                </div>
                <div className="card-pf-body">
                    {syspurpose_status}
                    {sla}
                    {usage}
                    {role}
                    {add_ons}
                </div>
            </div>
        );
    }
}

class InsightsStatusCard extends React.Component {
    constructor(props) {
        super(props);
    }
    render() {
        let insights;
        if (this.props.insights_available) {
            insights = <InsightsStatus/>;
        } else {
            insights = <p>Insights client is not installed.</p>
        }
        return (
            <div className="card-pf">
                <div className="card-pf-heading">
                    <h2 className="card-pf-title">
                        { _("Insights") }
                    </h2>
                </div>
                <div className="card-pf-body">
                    { insights }
                </div>
            </div>
        );
    }
}

class SystemStatusCard extends React.Component {
    constructor(props) {
        super(props);
    }
    render() {
        let label;
        let action;
        let note;
        let isUnregistering = (this.props.status === "unregistering");

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
            <div className="card-pf">
                <div className="card-pf-heading">
                    <h2 className="card-pf-title">
                        { _("Subscriptions") }
                    </h2>
                </div>
                <div className="card-pf-body">
                    { label }
                    { action }
                    { note }
                </div>
            </div>
        );
    }
}

/* Show subscriptions status of the system, offer to register/unregister the system
 * Expected properties:
 * status       subscription status
 * error        error message to show (in Curtains if not connected, as a dismissable alert otherwise)
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
            let error_msg = createFragment(this.props.error);
            errorMessage = (
                <DismissableError dismissError={this.props.dismissError}>{error_msg}</DismissableError>
            );
        }

        return (
            <div className="subscription-status-ct">
                {errorMessage}
                <div className="container-fluid container-cards-pf">
                    <div className="card-pf card-pf-view">
                        <div className="col-xs-6 col-sm-4 col-md-4">
                            <SystemStatusCard {...this.props } />
                            <SystemPurposeStatusCard {...this.props } />
                            <InsightsStatusCard {...this.props } />
                        </div>
                    </div>
                </div>
            </div>
        );
    }
}


/* Element used for representation of consumed subscription (entitlement). The element
 * has following properties:
 * state.enabled: true/false
 * remove_label: "Remove/Removing..."
 */
class ConsumedEntitlement extends React.Component {
    constructor(props) {
        super(props);
        this.state = { disabled: false };
        this.remove_label = _("Remove");
        this.props.consumedEntitlements[this.props.entitlement.pool_id] = this;
    }

    /**
     * Remove selected consumed subcrition and enable corresponding available subscription
     * @param event
     */
    removePool(event) {
        console.debug("removePool", event, this.props.entitlement.serial);
        if (event && event.button !== 0) {
            return;
        }
        console.debug("Button clicked");
        this.state.disabled = true;
        this.remove_label = _("Removing...");
        subscriptionsClient.removePool(this.props.entitlement.serial);
        this.props.parent.availableEntitlementComps[this.props.entitlement.pool_id].setState(
            {
                attached: false,
                attach_label: _("Attach")
            }
        );
    }

    renderActions() {
        return (
            <div>
                <Button
                    key={ "button-" + this.props.entitlement.serial }
                    id={ "button-" + this.props.entitlement.serial }
                    disabled={ this.state.disabled }
                    onClick={ event => this.removePool(event) }
                >{ this.remove_label }</Button>
            </div>
        )
    }

    /**
     * Render element representing consumed subscription
     */
    render() {
        let icon_name;

        // TODO: unplugged icon for not used subscriptions (consumed but no product installed
        //       from given entitlement)
        icon_name = "fa pficon-plugged";

        let products = this.props.entitlement.provides.map((product) =>
            <li key={product}>{ product }</li>
        );

        const renderActions = () => (
            <div>
                <Button
                    key={ this.props.entitlement.serial }
                    id={ this.props.entitlement.serial }
                    disabled={ this.state.disabled }
                    onClick={ event => this.removePool(event) }
                >{ this.remove_label }</Button>
            </div>
        );

        return (
            <ListViewItem
                leftContent={<ListViewIcon icon={ icon_name } />}
                heading={ this.props.entitlement.subscription_name }
                key={ this.props.entitlement.pool_id }
                id={ this.props.entitlement.pool_id }
                actions={renderActions()}
            >
                <Row>
                    <Col sm={11}>
                        <div className="col-md-11">
                            <dl className="dl-horizontal">
                                <dt>{ _("Subscription") }</dt>
                                <dd>{ this.props.entitlement.subscription_name }</dd>
                                <dt>{ _("Pool ID") }</dt>
                                <dd>{ this.props.entitlement.pool_id }</dd>
                                <dt>{ _("Serial")}</dt>
                                <dd>{ this.props.entitlement.serial }</dd>
                                <dt>{ _("SKU") }</dt>
                                <dd>{ this.props.entitlement.sku }</dd>
                                <dt>{ _("Service Level") }</dt>
                                <dd>{ this.props.entitlement.service_level }</dd>
                                <dt>{ _("Service Type") }</dt>
                                <dd>{ this.props.entitlement.service_type }</dd>
                                <dt>{ _("Roles") }</dt>
                                <dd>{ this.props.entitlement.roles }</dd>
                                <dt>{ _("Usage") }</dt>
                                <dd>{ this.props.entitlement.usage }</dd>
                                <dt>{ _("Add-ons") }</dt>
                                <dd>{ this.props.entitlement.addons }</dd>
                                <dt>{ _("Contract") }</dt>
                                <dd>{ this.props.entitlement.contract }</dd>
                                <dt>{ _("Account") }</dt>
                                <dd>{ this.props.entitlement.account }</dd>
                                <dt>{ _("Provides Management") }</dt>
                                <dd>{ this.props.entitlement.provides_management }</dd>
                                <dt>{ _("Quantity Used") }</dt>
                                <dd>{ this.props.entitlement.quantity_used }</dd>
                                <dt>{ _("Entitlement Type") }</dt>
                                <dd>{ this.props.entitlement.system_type }</dd>
                                <dt>{ _("Statud Setails") }</dt>
                                <dd>{ this.props.entitlement.status_details }</dd>
                                <dt>{ _("Provides") }</dt>
                                <dd><ul className="product-list">{ products }</ul></dd>
                                <dt>{ _("Starts") }</dt>
                                <dd>{ this.props.entitlement.starts }</dd>
                                <dt>{ _("Ends") }</dt>
                                <dd>{ this.props.entitlement.ends }</dd>
                            </dl>
                        </div>
                    </Col>
                </Row>
            </ListViewItem>
        );
    }
}


/* Element used for representation of available subscription (entitlement). The element has following
 * properties:
 * state.attached: true/false
 * attach_label: "Attach/Attaching.../Attached
 */
class AvailableEntitlement extends React.Component {
    constructor(props) {
        super(props);
        this.attachPool = this.attachPool.bind(this);
        this.renderActions = this.renderActions.bind(this);
        this.props.availableEntitlements[this.props.entitlement.id] = this;
        if (this.props.entitlement.id in this.props.parent.consumedEntitlementComps) {
            this.state = {
                attached: true,
                attach_label: _("Attached")
            };
        } else {
            this.state = {
                attached: false,
                attach_label: _("Attach")
            };
        }
    }

    /**
     * Thit method is used fot attaching selected subscription
     * @param event
     */
    attachPool(event) {
        console.debug("attachPool", event, this.props.entitlement.id);
        if (event && event.button !== 0) {
            return;
        }
        console.debug("Button clicked", this.props.entitlement.id);
        this.setState({ attached: true, attach_label: _("Attaching...")});
        subscriptionsClient.attachPool(this.props.entitlement.id);
        this.setState({ attach_label: _("Attached")});
    }

    /**
     * This method is used for rendering actions for list item representing
     * available subscription
     * @returns {*}
     */
    renderActions() {
        return (
            <div>
                <Button
                    key={ "button-" + this.props.entitlement.id }
                    id={ "button-" + this.props.entitlement.id }
                    disabled={ this.state.attached }
                    onClick={ event => this.attachPool(event) }
                >{ this.state.attach_label }</Button>
            </div>
        )
    }

    /**
     * Render item representing one available subscription
     * @returns {*}
     */
    render() {
        let icon_name;

        if (this.state.attached === true) {
            icon_name = "fa pficon-plugged";
        } else {
            icon_name = "fa pficon-unplugged";
        }

        let products = this.props.entitlement.providedProducts.map((product) =>
            <li key={product}>{ product }</li>
        );

        return (
            <ListViewItem
                leftContent={<ListViewIcon icon={ icon_name } />}
                heading={ this.props.entitlement.productName }
                key={ this.props.entitlement.id }
                id={ this.props.entitlement.id }
                actions={ this.renderActions() }
            >
                <Row>
                    <Col sm={11}>
                        <div className="col-md-11">
                            <dl className="dl-horizontal">
                                <dt>{ _("Subscription") }</dt>
                                <dd>{ this.props.entitlement.productName }</dd>
                                <dt>{ _("Provides") }</dt>
                                <dd><ul className="product-list">{ products }</ul></dd>
                                <dt>{ _("Pool ID") }</dt>
                                <dd>{ this.props.entitlement.id }</dd>
                                <dt>{ _("SKU") }</dt>
                                <dd>{ this.props.entitlement.productId }</dd>
                                <dt>{ _("Contract") }</dt>
                                <dd>{ this.props.entitlement.contractNumber }</dd>
                                <dt>{ _("Provides Management") }</dt>
                                <dd>{ this.props.entitlement.management_enabled }</dd>
                                <dt>{ _("Available") }</dt>
                                <dd>{ this.props.entitlement.quantity }</dd>
                                <dt>{ _("Service Type") }</dt>
                                <dd>{ this.props.entitlement.service_type }</dd>
                                <dt>{ _("Roles") }</dt>
                                <dd>{ this.props.entitlement.roles }</dd>
                                <dt>{ _("Service Level") }</dt>
                                <dd>{ this.props.entitlement.service_level }</dd>
                                <dt>{ _("Usage") }</dt>
                                <dd>{ this.props.entitlement.usage }</dd>
                                <dt>{ _("Add-ons") }</dt>
                                <dd>{ this.props.entitlement.addons }</dd>
                                <dt>{ _("Subscription Type") }</dt>
                                <dd>{ this.props.entitlement.pool_type }</dd>
                                <dt>{ _("Starts") }</dt>
                                <dd>{ this.props.entitlement.startDate }</dd>
                                <dt>{ _("Ends") }</dt>
                                <dd>{ this.props.entitlement.endDate }</dd>
                            </dl>
                        </div>
                    </Col>
                </Row>
            </ListViewItem>
        );
    }
}

class InstalledProduct extends React.Component {
    constructor() {
        super();
    }

    render() {
        let icon_name;
        let status_text;

        if (this.props.product.status === 'subscribed') {
            icon_name = "fa pficon-ok";
            status_text = _("Subscribed");
        } else {
            icon_name = "fa pficon-error-circle-o";
            status_text = _("Not Subscribed (Not supported by a valid subscription.)");
        }

        return (
            <ListViewItem
                leftContent={<ListViewIcon icon={ icon_name } />}
                heading={ this.props.product.productName }
                key={ this.props.product.productId }
                // Id has to be productName and not productId, because consumed subscription can reference
                // to the installed product only using productName
                id={ this.props.product.productName }
            >
                <Row>
                    <Col sm={11}>
                        <div className="col-md-11">
                            <dl className="dl-horizontal">
                                <dt>{ _("Product Name") }</dt>
                                <dd>{ this.props.product.productName }</dd>
                                <dt>{ _("Product ID") }</dt>
                                <dd>{ this.props.product.productId }</dd>
                                <dt>{ _("Version") }</dt>
                                <dd>{ this.props.product.version }</dd>
                                <dt>{ _("Arch") }</dt>
                                <dd>{ this.props.product.arch }</dd>
                                <dt>{ _("Status") }</dt>
                                <dd>{ status_text }</dd>
                                <dt>{ _("Starts") }</dt>
                                <dd>{ this.props.product.starts }</dd>
                                <dt>{ _("Ends") }</dt>
                                <dd>{ this.props.product.ends }</dd>
                            </dl>
                        </div>
                    </Col>
                </Row>
            </ListViewItem>
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
    constructor() {
        super();
        // this.intalledProductComps = {};
        this.consumedEntitlementComps = {};
        this.availableEntitlementComps = {};
    }

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
        } else if (this.props.status === undefined && !subscriptionsClient.config.loaded) {
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
        // let productEntries = this.props.products.map(this.renderProduct);
        let productEntries = this.props.products.map((item) => {
            return (
                <InstalledProduct key={ item.productId } product={ item }/>
            );
        });
        let consumedEntitlementEntries = this.props.consumedEntitlements.map((item) => {
            return (
                <ConsumedEntitlement
                    key={ item.serial }
                    entitlement={ item }
                    consumedEntitlements={ this.consumedEntitlementComps }
                    parent={ this }
                />
            );
        });
        let availableEntitlementEntries = this.props.availableEntitlements.map((item) => {
            return (
                <AvailableEntitlement
                    key={ item.id }
                    entitlement={ item }
                    availableEntitlements={ this.availableEntitlementComps }
                    parent={ this }
                />
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
                        { productEntries }
                    </ListView>
                </Listing>
                <Listing
                    title={ _("Consumed subscriptions") }
                    emptyCaption={ _("No consumed subscriptions detected.")}
                >
                    <ListView className="consumed-subscriptions">
                        { consumedEntitlementEntries }
                    </ListView>
                </Listing>
                <Listing
                    title={ _("Available subscriptions") }
                    emptyCaption={ _("No available subscriptions detected.")}
                >
                    <ListView className="available-subscriptions">
                        { availableEntitlementEntries }
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
