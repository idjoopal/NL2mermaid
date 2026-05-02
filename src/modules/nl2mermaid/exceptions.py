class NL2MermaidException(Exception):
    pass


class GenerationFailedError(NL2MermaidException):
    pass


class InvalidQueryError(NL2MermaidException):
    pass
