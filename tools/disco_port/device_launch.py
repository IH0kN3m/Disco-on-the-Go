"""Keep CoreDevice options out of the launched game's remaining arguments."""

from .binary import FormatError


def launch_arguments(device, bundle, output, mip_limit=None, lazy_scenes=False):
    import json
    arguments = ['xcrun', 'devicectl', 'device', 'process', 'launch', '--device', device,
                 '--terminate-existing', '--timeout', '45', '--json-output', str(output)]
    environment = {}
    if mip_limit is not None:
        if type(mip_limit) is not int or mip_limit not in range(4):
            raise FormatError('Unsupported texture mip limit')
        environment['DISCO_TEXTURE_MIP_LIMIT'] = str(mip_limit)
    if type(lazy_scenes) is not bool:
        raise FormatError('Invalid scene residency option')
    if lazy_scenes:
        environment['DISCO_LAZY_SCENES'] = '1'
    if environment:
        arguments += ['--environment-variables', json.dumps(environment)]
    return arguments + [bundle]


def validate_launch(result, mip_limit=None, lazy_scenes=False):
    options = result.get('launchOptions', {})
    if options.get('terminateExistingInstances') is not True or options.get('arguments'):
        raise FormatError('CoreDevice options were not applied to the launch')
    if mip_limit is not None and options.get('environmentVariables', {}).get('DISCO_TEXTURE_MIP_LIMIT') != str(mip_limit):
        raise FormatError('CoreDevice did not pass the texture diagnostic setting')
    if lazy_scenes and options.get('environmentVariables', {}).get('DISCO_LAZY_SCENES') != '1':
        raise FormatError('CoreDevice did not enable scene residency adapter')
    pid = result.get('process', {}).get('processIdentifier')
    if type(pid) is not int or pid <= 0:
        raise FormatError('Launch returned no valid process identifier')
    return pid
