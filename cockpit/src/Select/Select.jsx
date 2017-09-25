import React from 'react';
import $ from 'jquery';
import 'bootstrap';
import 'bootstrap-select';

const PropTypes = React.PropTypes;

/* React pattern component for a dropdown/select control */
class Select extends React.Component {
    componentDidMount() {
        this.$el = $(this.el);
        this.$el.selectpicker().change(this.props.onChange);
    }

    componentWillUnmount() {
        this.$el.selectpicker('destroy');
    }

    render() {
        return (
            <div>
                <select id={this.props.id} className="selectpicker" ref={el => this.el = el}>
                    {this.props.children}
                </select>
            </div>
        );
    }
}

Select.propTypes = {
    onChange: PropTypes.func,
    id: PropTypes.string,
    children: PropTypes.arrayOf(PropTypes.element),
};

export default Select;
