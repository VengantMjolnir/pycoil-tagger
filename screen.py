class Screen:
    name = ''
    root = None

    def __init__(self, name):
        self.name = name
        pass

    def enter(self):
        pass

    def exit(self):
        pass

    def update(self):
        pass

    def event(self, event):
        pass

    def render(self, surface):
        pass


class ScreenManager:
    screen_list = list(())
    screen_lookup = dict()
    current = None
    prev = None

    def __init__(self):
        pass

    def add_screen(self, screen):
        self.screen_list.append(screen)
        self.screen_lookup[screen.name] = screen

    def find_screen(self, screen_name):
        if screen_name in self.screen_lookup:
            return self.screen_lookup[screen_name]
        return None

    def update(self):
        if self.current is not None:
            self.current.update()

    def move_to(self, screen_name):
        screen = self.find_screen(screen_name)
        if screen is None or screen == self.current:
            print 'No screen found with name ' + screen_name
            return

        if self.current is not None:
            self.current.exit()

        self.prev = self.current
        self.current = screen

        if self.current is not None:
            self.current.enter()

    def return_to_prev(self):
        if self.prev is not None:
            self.move_to(self.prev.name)

    def event(self, event):
        if self.current is not None:
            self.current.event(event)

    def render(self, surface):
        if self.current is not None:
            self.current.render(surface)
