import React from 'react';
import 'bootstrap';
import 'bootstrap-select';
import PropTypes from 'prop-types';

/* React pattern component for a dropdown/select control */
class Select extends React.Component {
    render() {
        return (
            <div>
                <select className="form-control" {...this.props}>
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
