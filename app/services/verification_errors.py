class VerificationNotFoundError(Exception):
    pass


class VerificationAlreadyRunError(Exception):
    pass


class NoNewsArticlesError(Exception):
    pass


class NewsProviderUnavailableError(Exception):
    pass


class AIProviderUnavailableError(Exception):
    pass
