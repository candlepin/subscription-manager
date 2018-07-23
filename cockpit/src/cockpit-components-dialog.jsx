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
import ReactDOM from 'react-dom';
import PropTypes from 'prop-types';

let _ = cockpit.gettext;

/*
 * React template for a Cockpit dialog footer
 * It can display an error, wait for an action to complete,
 * has a 'Cancel' button and an action button (defaults to 'OK')
 * Expected props:
 *  - cancel_clicked optional
 *     Callback called when the dialog is canceled
 *  - cancel_style
 *     css class used for the cancel button, defaults to 'cancel'
 *  - cancel_caption optional, defaults to 'Cancel'
 *  - list of actions, each an object with:
 *      - clicked
 *         Callback function that is expected to return a promise.
 *         parameter: callback to set the progress text (will be displayed next to spinner)
 *      - caption optional, defaults to 'Ok'
 *      - disabled optional, defaults to false
 *      - style defaults to 'default', other options: 'primary', 'danger'
 *  - static_error optional, always show this error
 *  - dialog_done optional, callback when dialog is finished (param true if success, false on cancel)
 */
class DialogFooter extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            action_in_progress: false,
            action_in_progress_promise: null,
            action_progress_message: '',
            action_canceled: false,
            error_message: null,
        };
    }
    keyUpHandler(e) {
        if (e.keyCode === 27) {
            this.cancel_click();
            e.stopPropagation();
        }
    }
    componentDidMount() {
        document.body.classList.add("modal-in");
        document.addEventListener('keyup', event => this.keyUpHandler(event));
    }
    componentWillUnmount() {
        document.body.classList.remove("modal-in");
        document.removeEventListener('keyup', event => this.keyUpHandler(event));
    }
    update_progress(msg) {
        this.setState({ action_progress_message: msg });
    }
    action_click(handler, event) {
        // only consider clicks with the primary button
        if (event && event.button !== 0)
            return;
        let self = this;
        this.setState({
            error_message: null,
            action_progress_message: '',
            action_in_progress: true,
            action_canceled: false,
        });
        this.state.action_in_progress_promise = handler(message => this.update_progress(message))
            .done(function() {
                self.setState({ action_in_progress: false, error_message: null });
                if (self.props.dialog_done)
                    self.props.dialog_done(true);
            })
            .fail(function(error) {
                if (self.state.action_canceled) {
                    if (self.props.dialog_done)
                        self.props.dialog_done(false);
                }

                /* Always log global dialog errors for easier debugging */
                console.warn(error);

                self.setState({ action_in_progress: false, error_message: String(error) });
            })
            .progress(message => this.update_progress(message));
        if (event)
            event.stopPropagation();
    }
    cancel_click(event) {
        // only consider clicks with the primary button
        if (event && event.button !== 0)
            return;

        this.setState({action_canceled: true});
        if (this.props.cancel_clicked)
            this.props.cancel_clicked();
        // an action might be in progress, let that handler decide what to do if they added a cancel function
        if (this.state.action_in_progress && 'cancel' in this.state.action_in_progress_promise) {
            this.state.action_in_progress_promise.cancel();
            return;
        }
        if (this.props.dialog_done)
            this.props.dialog_done(false);
        if (event)
            event.stopPropagation();
    }
    render() {
        let cancel_caption, cancel_style;
        if ('cancel_caption' in this.props)
            cancel_caption = this.props.cancel_caption;
        else
            cancel_caption = _("Cancel");

        if ('cancel_style' in this.props)
            cancel_style = this.props.cancel_style;
        else
            cancel_style = "cancel";
        cancel_style = "btn btn-default " + cancel_style;

        // If an action is in progress, show the spinner with its message and disable all actions except cancel
        let wait_element;
        let actions_disabled;
        if (this.state.action_in_progress) {
            actions_disabled = 'disabled';
            wait_element = <div className="dialog-wait-ct pull-left">
                <div className="spinner spinner-sm"/>
                <span>{ this.state.action_progress_message }</span>
            </div>;
        }

        let self = this;
        let action_buttons = this.props.actions.map(function(action) {
            let caption;
            if ('caption' in action)
                caption = action.caption;
            else
                caption = _("Ok");

            let button_style = "btn-default";
            let button_style_mapping = { 'primary': 'btn-primary', 'danger': 'btn-danger' };
            if ('style' in action && action.style in button_style_mapping)
                button_style = button_style_mapping[action.style];
            button_style = "btn " + button_style + " apply";
            let action_disabled = actions_disabled || ('disabled' in action && action.disabled);
            return (<button
                    key={ caption }
                    className={ button_style }
                    onClick={event => self.action_click(action.clicked, event)}
                    disabled={ action_disabled }
                >{ caption }</button>
            );
        });

        // If we have an error message, display the error
        let error_element;
        let error_message;
        if (this.props.static_error !== undefined && this.props.static_error !== null)
            error_message = this.props.static_error;
        else
            error_message = this.state.error_message;
        if (error_message) {
            error_element = <div className="alert alert-danger dialog-error">
                <span className="fa fa-exclamation-triangle"/>
                <span>{ error_message }</span>
            </div>;
        }
        return (
            <div className="modal-footer">
                { error_element }
                { wait_element }
                <button
                    className={ cancel_style }
                    onClick={event => this.cancel_click(event)}
                >{ cancel_caption }</button>
                { action_buttons }
            </div>
        );
    }
}

DialogFooter.propTypes = {
    cancel_clicked: PropTypes.func,
    cancel_caption: PropTypes.string,
    cancel_style: PropTypes.string,
    actions: PropTypes.array,
    static_error: PropTypes.string,
    dialog_done: PropTypes.func,
};

/*
 * React template for a Cockpit dialog
 * The primary action button is disabled while its action is in progress (waiting for promise)
 * Removes focus on other elements on showing
 * Expected props:
 *  - title (string)
 *  - no_backdrop optional, skip backdrop if true
 *  - body (react element, top element should be of class modal-body)
 *      It is recommended for information gathering dialogs to pass references
 *      to the input components to the controller. That way, the controller can
 *      extract all necessary information (e.g. for input validation) when an
 *      action is triggered.
 *  - footer (react element, top element should be of class modal-footer)
 *  - id optional, id that is assigned to the top level dialog node, but not the backdrop
 */
class Dialog extends React.Component{
    static componentDidMount() {
        // if we used a button to open this, make sure it's not focused anymore
        if (document.activeElement)
            document.activeElement.blur();
    }
    render() {
        let backdrop;
        if (!this.props.no_backdrop) {
            backdrop = <div className="modal-backdrop fade in"/>;
        }
        return (
            <div>
                { backdrop }
                <div className="modal fade in dialog-ct-visible" tabIndex="-1">
                    <div id={this.props.id} className="modal-dialog">
                        <div className="modal-content">
                            <div className="modal-header">
                                <h4 className="modal-title">{ this.props.title }</h4>
                            </div>
                            { this.props.body }
                            { this.props.footer }
                        </div>
                    </div>
                </div>
            </div>
        );
    }
}

Dialog.propTypes = {
    title: PropTypes.string.isRequired,
    no_backdrop: PropTypes.bool,
    body: PropTypes.element.isRequired,
    footer: PropTypes.element.isRequired,
    id: PropTypes.string,
};

/* Create and show a dialog
 * For this, create a containing DOM node at the body level
 * The returned object has the following methods:
 *     - setFooterProps replace the current footerProps and render
 *     - setProps       replace the current props and render
 *     - render         render again using the stored props
 * The DOM node and React metadata are freed once the dialog has closed
 */
let show_modal_dialog = function(props, footerProps) {
    let dialogName = 'cockpit_modal_dialog';
    // don't allow nested dialogs
    if (document.getElementById(dialogName)) {
        console.warn('Unable to create nested dialog');
        return;
    }
    // create an element to render into
    let rootElement = document.createElement("div");
    rootElement.id = dialogName;
    document.body.appendChild(rootElement);

    // register our own on-close callback
    let origCallback;
    let closeCallback = function() {
        if (origCallback)
            origCallback.apply(this, arguments);
        ReactDOM.unmountComponentAtNode(rootElement);
        rootElement.remove();
    };

    let dialogObj = { };
    dialogObj.props = null;
    dialogObj.footerProps = null;
    dialogObj.render = function() {
        dialogObj.props.footer = <DialogFooter {...dialogObj.footerProps} />;
        ReactDOM.render(<Dialog {...dialogObj.props} />, rootElement);
    };
    function updateFooterAndRender() {
        if (dialogObj.props === null || dialogObj.props === undefined)
            dialogObj.props = { };
        dialogObj.props.footer = <DialogFooter {...dialogObj.footerProps} />;
        dialogObj.render();
    }
    dialogObj.setFooterProps = function(footerProps) {
        /* Always log error messages to console for easier debugging */
        if (footerProps.static_error)
            console.warn(footerProps.static_error);
        dialogObj.footerProps = footerProps;
        if (dialogObj.footerProps === null || dialogObj.footerProps === undefined)
            dialogObj.footerProps = { };
        if (dialogObj.footerProps.dialog_done !== closeCallback) {
            origCallback = dialogObj.footerProps.dialog_done;
            dialogObj.footerProps.dialog_done = closeCallback;
        }
        updateFooterAndRender();
    };
    dialogObj.setProps = function(props) {
        dialogObj.props = props;
        updateFooterAndRender();
    };
    dialogObj.setFooterProps(footerProps);
    dialogObj.setProps(props);

    // now actually render
    dialogObj.render();

    return dialogObj;
};

module.exports = {
    Dialog: Dialog,
    DialogFooter: DialogFooter,
    show_modal_dialog: show_modal_dialog,
};
