/*
 * This file is part of Cockpit.
 *
 * Copyright (C) 2019 Red Hat, Inc.
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

import cockpit from "cockpit";
import React from "react";
import moment from "moment";

import { show_modal_dialog } from "./cockpit-components-dialog.jsx";
import * as service from "../lib/service.js";

import subscriptionsClient from './subscriptions-client';

let _ = cockpit.gettext;

moment.locale(cockpit.language);

const insights_timer = service.proxy("insights-client.timer", "Timer");
const insights_service = service.proxy("insights-client.service", "Service");

export function detect() {
    return cockpit.spawn([ "which", "insights-client" ], { err: "ignore" }).then(() => true, () => false);
}

function catch_error(err) {
    let msg = err.toString();
    // The insights-client frequently dumps
    // Python backtraces on us. Make them more
    // readable by wrapping the text in <pre>.
    if (msg.indexOf("\n") > 0)
        msg = <pre>{msg}</pre>;
    subscriptionsClient.setError("error", msg);
}

export function register() {
    return cockpit.spawn([ "insights-client", "--register" ], { superuser: true, err: "message" })
        .catch(catch_error);
}

export function unregister() {
    if (insights_timer.enabled) {
        return cockpit.spawn([ "insights-client", "--unregister" ], { superuser: true, err: "message" })
            .catch(catch_error);
    } else {
        return cockpit.resolve();
    }
}

// TODO - generalize this to arbitrary number of arguments (when needed)
export function arrfmt(fmt, arg) {
    var index = fmt.indexOf("$0");
    if (index >= 0)
        return [ fmt.slice(0, index), arg, fmt.slice(index + 2) ];
    else
        return [ fmt ];
}

function left(func) {
    return function (event) {
        if (!event || event.button !== 0)
            return;
        func();
        event.stopPropagation();
    };
}

export const blurb =
    _("Proactively identify and remediate threats to security, performance, availability, and stability with Red Hat Insights \u2014 with predictive analytics, avoid problems and unplanned downtime in your Red Hat environment.");

export const link =
    <a href="https://www.redhat.com/en/technologies/management/insights" target="_blank" rel="noopener">Red Hat Insights <i className="fa fa-external-link"/></a>;

function show_connect_dialog() {
    show_modal_dialog(
        {
            title: _("Connect to Red Hat Insights"),
            body: (
                <div className="modal-body">
                    <strong>{ arrfmt(_("This system is not connected to $0."), link) }</strong>
                    <p>{blurb}</p>
                </div>
            )
        },
        {
            actions: [
                {
                    caption: _("Connect"),
                    style: "primary",
                    clicked: () => register().catch(catch_error)
                }
            ]
        }
    );
}

class Revealer extends React.Component {
    constructor() {
        super();
        this.state = { revealed: false };
    }

    render() {
        return (
            <div>
                <a onClick={event => { if (event.button == 0) this.setState({ revealed: !this.state.revealed }); }}>
                   {this.props.summary}
                </a> <i className={this.state.revealed ? "fa fa-angle-down" : "fa fa-angle-right"}/>
                <br/>
                {this.state.revealed && this.props.children}
            </div>
        );
    }
}

const get_monotonic_start = cockpit.spawn(
    [ "/usr/libexec/platform-python", "-c",
      "import time; print(time.clock_gettime(time.CLOCK_REALTIME) - time.clock_gettime(time.CLOCK_MONOTONIC))"
    ]).then(data => {
        return parseFloat(data);
    });

function calc_next_elapse(monotonic_start, timer) {
    let next_mono = Infinity, next_real = Infinity;
    if (monotonic_start) {
        if (timer.NextElapseUSecMonotonic)
            next_mono = timer.NextElapseUSecMonotonic / 1e6 + monotonic_start;
        if (timer.NextElapseUSecRealtime)
            next_real = timer.NextElapseUSecRealtime / 1e6;
    }
    let next = Math.min(next_mono, next_real);
    if (next !== Infinity)
        return moment(next * 1000).calendar();
    else
        return _("unknown");
}

function jump_to_service() {
    cockpit.jump("/system/services#/insights-client.service", cockpit.transport.host);
}

function jump_to_timer() {
    cockpit.jump("/system/services#/insights-client.timer", cockpit.transport.host);
}

function monitor_last_upload() {
    let self = {
        timestamp: 0,
        results: null,

        close: close
    };

    cockpit.event_target(self);

    let results_file = cockpit.file("/etc/insights-client/.last-upload.results", { syntax: JSON });
    results_file.watch(data => {
        self.results = data;
        cockpit.spawn([ "stat", "-c", "%Y", "/etc/insights-client/.last-upload.results" ], { err: "message" })
            .then(ts => {
                self.timestamp = parseInt(ts);
                self.dispatchEvent("changed");
            })
            .catch(() => {
                self.timestamp = 0;
                self.dispatchEvent("changed");
            });
    });

    function close() {
        results_file.close();
    }

    return self;
}

const last_upload_monitor = monitor_last_upload();

function show_status_dialog() {
    function show(monotonic_start) {
        let lastupload = last_upload_monitor.timestamp;
        let next_elapse = calc_next_elapse(monotonic_start, insights_timer.details);

        let failed_text = null;
        if (insights_service.unit.ActiveExitTimestamp &&
            insights_service.unit.ActiveExitTimestamp / 1e6 > lastupload) {
            lastupload = insights_service.unit.ActiveExitTimestamp / 1e6;
            failed_text = _("The last Insights data upload has failed.");
        }

        let dlg = show_modal_dialog(
            {
                title: _("Connected to Red Hat Insights"),
                body: (
                        <div className="modal-body">
                          <table>
                            <tbody>
                              <tr>
                                <th style={{ textAlign: "right", paddingRight: "1em" }}>Next Insights data upload</th>
                                <td>{next_elapse}</td>
                              </tr>
                              { lastupload ?
                              <tr>
                                <th style={{ textAlign: "right", paddingRight: "1em" }}>Last Insights data upload</th>
                                <td>{moment(lastupload * 1000).calendar()}</td>
                               </tr> : null
                              }
                            </tbody>
                          </table>
                          <br/>
                          { insights_timer.state == "failed" &&
                          <div className="alert alert-warning">
                            <span className="pficon pficon-warning-triangle-o"/>
                              {_("Next Insights data upload could not be scheduled.")}{" "}
                              <a onClick={left(jump_to_timer)}>{_("Details")}</a>
                          </div>
                          }
                          { insights_service.state == "failed" && failed_text &&
                          <div className="alert alert-warning">
                            <span className="pficon pficon-warning-triangle-o"/>
                              {failed_text}{" "}
                              <a onClick={left(jump_to_service)}>{_("Details")}</a>
                          </div>
                          }
                          <Revealer summary={_("Disconnect from Insights")}>
                            <div className="alert alert-warning"
                                 style={{ "padding": "14px", "marginTop": "1ex", "marginBottom": "0px" }}>
                              <p>{_("If you disconnect this system from Insights, it will no longer report it's Insights status in Red Hat Cloud or Satellite.")}</p>
                              <br/>
                              <button className="btn btn-danger" onClick={left(disconnect)}>
                                {_("Disconnect from Insights")}
                              </button>
                            </div>
                          </Revealer>
                        </div>
                )
            },
            {
                cancel_caption: _("Close"),
                actions: [ ]
            }
        );

        function disconnect() {
            dlg.setFooterProps(
                {
                    cancel_caption: _("Cancel"),
                    actions: [ ],
                    idle_message: <div className="spinner spinner-sm"/>
                });
            unregister().then(
                () => {
                    dlg.footerProps.dialog_done();
                },
                error => {
                    dlg.setFooterProps(
                        {
                            cancel_caption: _("Close"),
                            actions: [ ],
                            static_error: error.toString()
                        });
                })
        }
    }

    get_monotonic_start.then(show).catch(err => { console.warn(err); show(null) });
}


export class InsightsStatus extends React.Component {
    constructor() {
        super();
        this.state = { };
        this.on_changed = () => { this.setState({ }) };
    }

    componentDidMount() {
        insights_timer.addEventListener("changed", this.on_changed);
        insights_service.addEventListener("changed", this.on_changed);
        last_upload_monitor.addEventListener("changed", this.on_changed);
        this.status_file = cockpit.file("/var/lib/insights/status.json", { syntax: JSON });
        this.status_file.watch(data => { this.setState({ upload_status: data }); });
    }

    componentWillUnmount() {
        insights_timer.removeEventListener("changed", this.on_changed);
        insights_service.removeEventListener("changed", this.on_changed);
        last_upload_monitor.removeEventListener("changed", this.on_changed);
        this.status_file.close();
    }

    render() {
        let status;

        if (!insights_timer.exists || !insights_service.exists)
            return null;

        if (insights_timer.enabled) {
            let warn = (insights_service.state == "failed" &&
                        insights_service.unit.ActiveExitTimestamp &&
                        insights_service.unit.ActiveExitTimestamp / 1e6 > last_upload_monitor.timestamp);

            let result_link = "http://cloud.redhat.com/insights";
            if (this.state.upload_status && this.state.upload_status.insights_url)
                result_link = this.state.upload_status.insights_url;

            let rule_hits = null;
            if (this.state.upload_status && this.state.upload_status.reports)
                rule_hits = cockpit.format(cockpit.ngettext("($0 rule hit)", "($0 rule hits)",
                                                            this.state.upload_status.reports.length),
                                           this.state.upload_status.reports.length);

            status = (
                    <div style={{display: "inline-block", verticalAlign: "top" }}>
                    <a onClick={left(show_status_dialog)}>{_("Connected to Insights")}</a>
                    { warn && [ " ", <i className="pficon pficon-warning-triangle-o"/> ] }
                    <br/>
                    <a href={result_link} target="_blank" rel="noopener">
                    View your Insights results <i className="fa fa-external-link"/>
                    </a>
                    { rule_hits && <br/> }
                    { rule_hits }
                </div>
            );
        } else {
            status = <a onClick={left(show_connect_dialog)}>{_("Not connected")}</a>;
        }

        return <div><label>Insights: {status}</label></div>;
    }
}
