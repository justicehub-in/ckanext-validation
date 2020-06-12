# encoding: utf-8
import json

import six
import tableschema
from ckanext.scheming.validation import scheming_validator
from ckantoolkit import Invalid, config

from ckan.plugins.toolkit import _, missing

# Note: repeating_links and repeating_links_output are taken from:
# https://github.com/open-data/ckanext-repeating/blob/master/ckanext/repeating/validators.py

# Input validators

def resource_schema_validator(value, context):
    '''
    '''
    if not value:
        return

    msg = None

    if isinstance(value, basestring):

        if value.lower().startswith('http'):
            return value

        try:
            descriptor = json.loads(str(value))
            if not isinstance(descriptor, dict):
                msg = u'Invalid Table Schema descriptor: {}'.format(value)
                raise Invalid(msg)

        except ValueError as e:
            msg = u'JSON error in Table Schema descriptor: {}'.format(e)
            raise Invalid(msg)
    else:
        descriptor = value

    try:
        tableschema.validate(descriptor)
    except tableschema.exceptions.ValidationError as e:
        errors = []
        for error in e.errors:
            errors.append(error.message)
        msg = u'Invalid Table Schema: {}'.format(u', '.join(errors))

    if msg:
        raise Invalid(msg)

    return json.dumps(descriptor)


def validation_options_validator(value, context):
    '''Add default validation options if not already present

    At this point the value should already be a valid JSON string (ie
    `scheming_valid_json_object` has been run).
    '''

    default_options = config.get(
        'ckanext.validation.default_validation_options')

    if default_options:
        default_options = json.loads(default_options)

        provided_options = json.loads(value)

        default_options.update(provided_options)

        value = json.dumps(default_options, indent=None, sort_keys=True)

    return value


@scheming_validator
def scheming_multiple_choice_with_other(field, schema):
    """
    Accept zero or more values from a list of choices and convert
    to a json list for storage:

    1. a list of strings, eg.:

       ["choice-a", "choice-b"]

    2. a single string for single item selection in form submissions:

       "choice-a"
    """
    static_choice_values = None
    if 'choices' in field:
        static_choice_order = [c['value'] for c in field['choices']]
        static_choice_values = set(static_choice_order)

    def validator(key, data, errors, context):
        # if there was an error before calling our validator
        # don't bother with our validation
        if errors[key]:
            return

        value = data[key]
        if value is not missing:
            if isinstance(value, six.string_types):
                value = [value]
            elif not isinstance(value, list):
                errors[key].append(_('expecting list of strings'))
                return
        else:
            value = []

        choice_values = static_choice_values
        if not choice_values:
            choice_order = [c['value'] for c in sh.scheming_field_choices(field)]
            choice_values = set(choice_order)

        selected = set()
        for element in value:
            selected.add(element)

            if element and element not in static_choice_order:
                static_choice_order.append(element)
            continue

        if not errors[key]:
            data[key] = ','.join([v for v in
                (static_choice_order if static_choice_values else choice_order)
                if v in selected])

            if field.get('required') and not selected:
                errors[key].append(_('Select at least one'))

    return validator
