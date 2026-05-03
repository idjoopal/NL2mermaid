class PptGeneratorException(Exception):
    pass


class TemplateNotFoundError(PptGeneratorException):
    pass


class SlideGenerationError(PptGeneratorException):
    pass
