from abc import ABC, abstractmethod

class BasePage(ABC):
    def __init__(self, page):
        self.page = page

    @abstractmethod
    def navigate(self):
        pass