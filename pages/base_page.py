"""Base class for all Page Object Model (POM) page classes.

Every concrete page (e.g., UsersPage, LoginPage) must subclass BasePage and
implement navigate(). This enforces a consistent interface so test code can
always call page.navigate() regardless of which page object it holds.
"""

from abc import ABC, abstractmethod


class BasePage(ABC):
    """Abstract base for Playwright page wrappers.

    Subclasses receive the Playwright Page object at construction time and
    are responsible for encapsulating all locator and action logic for one
    logical page of the application under test.
    """

    def __init__(self, page):
        """Store the Playwright Page instance for use by subclass methods."""
        self.page = page

    @abstractmethod
    def navigate(self):
        """Navigate the browser to this page's URL.

        Implementations should call self.page.goto(<url>) and wait for
        the page to reach a known ready state before returning.
        """
