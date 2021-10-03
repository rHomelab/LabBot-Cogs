from redbot.core.commands import BadArgument, CommandError


class TagsCogException(CommandError):
    """
    Base exception class for all tags cog exceptions to be derived from.
    All subclasses of this class must override the __str__ magic method to return a user-friendly message.
    """


class TagNotFound(TagsCogException):
    """Raised when a tag could not be found in the config."""

    def __str__(self):
        return "No tag with this name was found."


class CanNotManageTag(TagsCogException):
    """Raised when the current user can not manage the tag specified."""

    def __str__(self):
        return "You are not authorised to manage this tag."


class TagConversionFailed(BadArgument):
    """Raised when a tag could not be found via the tag converter"""

    def __str__(self):
        return "No tag with this name was found."
