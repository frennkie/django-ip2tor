class PortInUseError(Exception):
    """The port is already in use"""
    pass


class PortNotInUseError(Exception):
    """The port is currently not in use"""
    pass
