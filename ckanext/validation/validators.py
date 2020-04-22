# encoding: utf-8
import json

import tableschema
from ckan.plugins.toolkit import _, missing
from ckantoolkit import Invalid, config

# Note: repeating_links and repeating_links_output are taken from:
# https://github.com/open-data/ckanext-repeating/blob/master/ckanext/repeating/validators.py

# Input validators

def resource_schema_validator(value, context):

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


def repeating_links(key, data, errors, context):
    """
    Accept repeating url input in the following forms
    and convert to a json list for storage:
    1. a list of strings, eg.
       ["http://example.com/article1", "http://example.com/article2"]
    2. a single string value to allow single text fields to be
       migrated to repeating text
       "http://example.com/article"
    """

    # just in case there was an error before our validator,
    # bail out here because our errors won't be useful
    if errors[key]:
        return

    value = data[key]
    # 1. list of strings or 2. single string
    if value is not missing:
        if isinstance(value, basestring):
            value = [value]
        if not isinstance(value, list):
            errors[key].append(_('expecting list of strings'))
            return

        out = []
        for element in value:
            if not isinstance(element, basestring):
                errors[key].append(_('invalid type for repeating text: %r')
                    % element)
                continue
            if isinstance(element, str):
                try:
                    element = element.decode('utf-8')
                except UnicodeDecodeError:
                    errors[key]. append(_('invalid encoding for "%s" value')
                        % lang)
                    continue
            out.append(element)

        if not errors[key]:
            data[key] = json.dumps(out)
        return

    # 3. separate fields
    found = {}
    prefix = key[-1] + '-'
    extras = data.get(key[:-1] + ('__extras',), {})

    for name, text in extras.iteritems():
        if not name.startswith(prefix):
            continue
        if not text:
            continue
        index = name.rsplit('-', 1)[1]
        try:
            index = int(index)
        except ValueError:
            continue
        found[index] = text

    out = [found[i] for i in sorted(found)]
    data[key] = json.dumps(out)


def repeating_links_output(value):
    """
    Return stored json representation as a list, if
    value is already a list just pass it through.
    """
    if isinstance(value, list):
        return value
    if value is None:
        return []
    try:
        return json.loads(value)
    except ValueError:
        return [value]
