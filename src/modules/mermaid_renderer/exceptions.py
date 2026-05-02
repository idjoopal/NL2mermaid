class MermaidRendererException(Exception):
    pass


class RenderFailedError(MermaidRendererException):
    pass


class InvalidMermaidCodeError(MermaidRendererException):
    pass
