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
import { InsightsStatus } from './insights.jsx';
import { EmptyStatePanel } from "../lib/cockpit-components-empty-state.jsx";
import { ListingTable } from "../lib/cockpit-components-table.jsx";
import { ExclamationCircleIcon } from '@patternfly/react-icons';
import {
    Alert, AlertGroup, AlertActionCloseButton, Button,
    Card, CardActions, CardBody, CardHeader, CardHeaderMain, CardTitle,
    DescriptionList, DescriptionListDescription, DescriptionListGroup, DescriptionListTerm,
    Gallery, Label, Page, PageSection, Split, SplitItem, Text, TextVariants,
} from '@patternfly/react-core';

let _ = cockpit.gettext;

class InstalledProducts extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            attaching_in_progress: false,
            attach_button_text: _("Auto-attach")
        };
        this.handleAutoAttach = this.handleAutoAttach.bind(this);
    }

    handleAutoAttach(event) {
        // only consider primary mouse button
        if (!event || event.button !== 0)
            return;
        if (this.props.autoAttach) {
            let self = this;
            this.setState({
                attaching_in_progress: true,
                attach_button_text: _("Auto-attaching ...")
            });
            this.props.autoAttach()
                    .done(function () {
                        self.setState({
                            attaching_in_progress: false,
                            attach_button_text: _("Auto-attach")
                        });
                    })
                    .fail(function () {
                        self.setState({
                            attaching_in_progress: false,
                            attach_button_text: _("Auto-attach")
                        });
                    });
        }
    }

    render() {
        let columnTitles = [_("Product name")];
        let entries = this.props.products.map(function (itm) {
            let subscribed;
            let status_text;
            let start_date_text;
            let end_date_text;

            if (itm.status === 'subscribed') {
                subscribed = true;
                status_text = _("Subscribed");

            } else {
                subscribed = false;
                status_text = _("Not subscribed (Not supported by a valid subscription)");
            }

            if (itm.starts.length === 0) {
                start_date_text = _("Unknown");
            } else {
                start_date_text = new Date(Date.parse(itm.starts)).toLocaleDateString();
            }

            if (itm.ends.length === 0) {
                end_date_text = _("Unknown");
            } else {
                end_date_text = new Date(Date.parse(itm.ends)).toLocaleDateString();
            }

            const columns = [
                { title: (<Split>
                    <SplitItem isFilled>
                        {itm.productName}
                    </SplitItem>
                    <SplitItem>
                        <Label color={subscribed ? "green" : "red"}>{subscribed ? _("Subscribed") : _("Not subscribed")}</Label>
                    </SplitItem>
                </Split>),
                  header: true,
                }
            ];

            const body = (
                <DescriptionList isHorizontal>
                    <DescriptionListGroup>
                        <DescriptionListTerm>{_("Product name")}</DescriptionListTerm>
                        <DescriptionListDescription>{itm.productName}</DescriptionListDescription>
                    </DescriptionListGroup>
                    <DescriptionListGroup>
                        <DescriptionListTerm>{_("Product ID")}</DescriptionListTerm>
                        <DescriptionListDescription>{itm.productId}</DescriptionListDescription>
                    </DescriptionListGroup>
                    <DescriptionListGroup>
                        <DescriptionListTerm>{_("Version")}</DescriptionListTerm>
                        <DescriptionListDescription>{itm.version}</DescriptionListDescription>
                    </DescriptionListGroup>
                    <DescriptionListGroup>
                        <DescriptionListTerm>{_("Arch")}</DescriptionListTerm>
                        <DescriptionListDescription>{itm.arch}</DescriptionListDescription>
                    </DescriptionListGroup>
                    <DescriptionListGroup>
                        <DescriptionListTerm>{_("Status")}</DescriptionListTerm>
                        <DescriptionListDescription>{status_text}</DescriptionListDescription>
                    </DescriptionListGroup>
                    <DescriptionListGroup>
                        <DescriptionListTerm>{_("Starts")}</DescriptionListTerm>
                        <DescriptionListDescription>{start_date_text}</DescriptionListDescription>
                    </DescriptionListGroup>
                    <DescriptionListGroup>
                        <DescriptionListTerm>{_("Ends")}</DescriptionListTerm>
                        <DescriptionListDescription>{end_date_text}</DescriptionListDescription>
                    </DescriptionListGroup>
                </DescriptionList>
            );

            return ({
                props: { key: itm.productId, 'data-row-id': itm.productName },
                columns,
                hasPadding: true,
                expandedContent: body,
            });
        });

        return (
            <Card id="products" className="products" key="products">
                <CardHeader>
                    <CardTitle><Text component={TextVariants.h2}>{_("Installed products")}</Text></CardTitle>
                    <CardActions>
                        <Button
                                isDisabled={this.state.attaching_in_progress || this.props.status === 'unknown'}
                                onClick={this.handleAutoAttach}>
                            { this.state.attach_button_text }
                        </Button>
                    </CardActions>
                </CardHeader>
                <CardBody className="contains-list">
                    <ListingTable aria-label={_("Installed products")}
                      variant='compact'
                      showHeader={false}
                      emptyCaption={_("No installed products detected")}
                      columns={columnTitles}
                      rows={entries} />
                </CardBody>
            </Card>
        );
    }
}

/* Show subscriptions status of the system, offer to register/unregister the system
 * Expected properties:
 * status       subscription status ID
 * status_msg   subscription status message
 * error        error message to show (in Curtains if not connected, as a dismissable alert otherwise)
 * syspurpose
 * syspurpose_status
 * dismissError callback, triggered for the dismissable error in connected state
 * register     callback, triggered when user clicks on register
 * unregister   callback, triggered when user clicks on unregister
 */
class SubscriptionStatus extends React.Component {
    constructor(props) {
        super(props);
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
        let syspurpose = null;
        const p = this.props.syspurpose;
        if (p["service_level_agreement"] || p["usage"] || p["role"] || p["addons"]) {
            syspurpose = (
                <Card id="syspurpose" key="syspurpose" className="ct-card-info">
                    <CardHeader>
                        <CardHeaderMain>
                            <Text className="purpose-header" component={TextVariants.h2}>{_("System purpose")}</Text>
                            {"(" + this.props.syspurpose_status + ")"}
                        </CardHeaderMain>
                    </CardHeader>
                    <CardBody>
                        <DescriptionList isHorizontal>
                            {p["service_level_agreement"] &&
                                <DescriptionListGroup>
                                    <DescriptionListTerm>{_("Service level")}</DescriptionListTerm>
                                    <DescriptionListDescription>{p["service_level_agreement"]}</DescriptionListDescription>
                                </DescriptionListGroup>
                            }
                            {p["usage"] &&
                                <DescriptionListGroup>
                                    <DescriptionListTerm>{_("Usage")}</DescriptionListTerm>
                                    <DescriptionListDescription>{p["usage"]}</DescriptionListDescription>
                                </DescriptionListGroup>
                            }
                            {p["role"] &&
                                <DescriptionListGroup>
                                    <DescriptionListTerm>{_("Role")}</DescriptionListTerm>
                                    <DescriptionListDescription>{p["role"]}</DescriptionListDescription>
                                </DescriptionListGroup>
                            }
                            {p["addons"] &&
                                <DescriptionListGroup>
                                    <DescriptionListTerm>{_("Add-ons")}</DescriptionListTerm>
                                    <DescriptionListDescription>{p["addons"]}</DescriptionListDescription>
                                </DescriptionListGroup>
                            }
                        </DescriptionList>
                    </CardBody>
                </Card>
            );
        }

        let label;
        let action;

        if (this.props.status === 'unknown') {
            label = _("Not registered");
            action = (
                <Button onClick={this.handleRegisterSystem}>{_("Register")}</Button>
            );
        } else {
            const isUnregistering = (this.props.status === "unregistering");
            label = this.props.status_msg;
            action = (
                <Button isDisabled={isUnregistering} isLoading={isUnregistering}
                              onClick={this.handleUnregisterSystem}>{isUnregistering ? _("Unregistering"): _("Unregister")}</Button>
            );
        }
        return (
            <>
                <Card id="overview" key="overview" className={ syspurpose !== null ? "ct-card-info" : "" }>
                    <CardHeader>
                        <CardTitle><Text component={TextVariants.h2}>{_("Overview")}</Text></CardTitle>
                        <CardActions>{action}</CardActions>
                    </CardHeader>
                    <CardBody>
                        <DescriptionList isHorizontal>
                            <DescriptionListGroup>
                                <DescriptionListTerm>{_("Subscription")}</DescriptionListTerm>
                                <DescriptionListDescription>{label}</DescriptionListDescription>
                            </DescriptionListGroup>
                            {(this.props.insights_available && this.props.status !== 'unknown') && <InsightsStatus />}
                        </DescriptionList>
                    </CardBody>
                </Card>
                {syspurpose}
            </>
        );
    }
}

/* Show subscriptions status of the system and registered products, offer to register/unregister the system
 * Expected properties:
 * status       subscription status ID
 * status_msg   subscription status message
 * error        error message to show (in EmptyState if not connected, as a dismissable alert otherwise
 * dismissError callback, triggered for the dismissable error in connected state
 * products     subscribed products (properties as in subscriptions-client)
 * register     callback, triggered when user clicks on register
 * unregister   callback, triggered when user clicks on unregister
 */
class SubscriptionsView extends React.Component {
    renderCurtains() {
        let loading = false;
        let description;
        let message;

        if (this.props.status === "service-unavailable") {
            message = _("The rhsm service is unavailable. Make sure subscription-manager is installed " +
                "and try reloading the page. Additionally, make sure that you have checked the " +
                "'Reuse my password for privileged tasks' checkbox on the login page.");
            description = _("Unable to the reach the rhsm service.");
        } else if (this.props.status === undefined && !subscriptionsClient.config.loaded) {
            loading = true;
            message = _("Updating");
            description = _("Retrieving subscription status...");
        } else if (this.props.status === 'access-denied') {
            message = _("Access denied");
            description = _("The current user isn't allowed to access system subscription status.");
        } else {
            message = _("Unable to connect");
            description = _("Couldn't get system subscription status. Please ensure subscription-manager is installed.");
        }

        return <EmptyStatePanel icon={loading ? null : ExclamationCircleIcon} paragraph={description} loading={loading} title={message} />;
    }

    renderSubscriptions() {
        let error = null;
        if (this.props.error) {
            let severity = this.props.error.severity || "danger";
            if (severity === "error")
                severity = "danger";
            error = (
                <AlertGroup isToast>
                    <Alert isLiveRegion variant={severity} title={this.props.error.msg.toString()}
                        actionClose={<AlertActionCloseButton onClose={this.props.dismissError} />} />
                </AlertGroup>
            );
        }

        return (
            <Page>
                <PageSection>
                    {error}
                    <Gallery className='ct-cards-grid' hasGutter>
                        <SubscriptionStatus { ...this.props } />
                        <InstalledProducts { ...this.props } />
                    </Gallery>
                </PageSection>
            </Page>
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

export default SubscriptionsView;
