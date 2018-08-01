import pygame
import pygame.display
from pygame.locals import *
from slicesprite import SliceSprite
import json


class Node(object):
    _container = None
    dirty = False
    abs_pos = (0, 0)
    pos = (0, 0)

    def __init__(self):
        pass

    @property
    def container(self):
        return self._container

    @container.setter
    def container(self, container):
        self._container = container
        self.dirty = True

    def position(self, x, y):
        self.pos = (x, y)
        self.dirty = True

    def get_abs_pos(self):
        if self._container is None:
            #print str(type(self)) + "No Container: " + str(self.pos)
            return self.pos

        if self.dirty is not True:
            return self.abs_pos

        container_pos = self._container.get_abs_pos()
        self.abs_pos = (self.pos[0] + container_pos[0], self.pos[1] + container_pos[1])
        #print str(type(self)) + "Dirty: ", self.abs_pos
        self.dirty = False
        return self.abs_pos


class Container(Node):
    def __init__(self):
        Node.__init__(self)
        self.children = list(())

    def add_object(self, child):
        self.children.append(child)
        child.container = self

    def remove_object(self, child):
        self.children.remove(child)
        child.container = None

    def event(self, event):
        for child in self.children:
            child.event(event)

    def update(self):
        for child in self.children:
            child.update()

    def render(self, screen):
        for child in self.children:
            child.render(screen)

    def position(self, x, y):
        Node.position(self, x, y)


class Panel(Container):
    def __init__(self, path, width, height):
        Container.__init__(self)
        with open(path) as file:
            data = json.load(file)
            slices = data["slice"]
            image = pygame.image.load(data["image"]).convert_alpha()
            self.image = SliceSprite(image, slicing=(slices["l"], slices["r"], slices["t"], slices["b"]))
        self.width = width
        self.height = height
        self.image.set_rect((0, 0, self.width, self.height))

    def event(self, event):
        Container.event(self, event)

    def update(self):
        Container.update(self)
        if self.dirty:
            self.position(self.pos[0], self.pos[1])

    def render(self, screen):
        if self.image is not None:
            self.image.render(screen)
        Container.render(self, screen)

    def position(self, x, y):
        Container.position(self, x, y)
        pos = self.get_abs_pos()
        self.image.set_rect((pos[0], pos[1], self.width, self.height))
        self.dirty = False


class Image:
    def __init__(self, path):
        self.image = pygame.image.load(path)
        self.pos = (0, 0)

    def event(self, event):
        pass

    def update(self):
        pass

    def render(self, screen):
        if self.image is not None:
            screen.blit(self.image, self.pos)

    def position(self, x, y):
        self.pos = (x, y)


class Label(Node):
    def __init__(self, font, text, color=(0, 0, 0)):
        Node.__init__(self)
        self.font = font
        self.text = text
        self.color = color
        self.cached_image = None

    def event(self, event):
        pass

    def update(self):
        if self.cached_image is None:
            self.cached_image = self.font.render(self.text, True, self.color)

    def render(self, screen):
        if self.cached_image is not None:
            screen.blit(self.cached_image, self.get_abs_pos())

    def position(self, x, y):
        Node.position(self, x, y)

    def set_text(self, text):
        self.text = text
        self.cached_image = None
        self.update()


class Bar(Node):
    left_fore = None
    mid_fore = None
    right_fore = None
    left_back = None
    mid_back = None
    right_back = None

    def __init__(self, path, width):
        Node.__init__(self)
        self.pos = (0, 0)
        self.percent = 1.0
        self.width = width
        self.mid_fg = None
        self.mid_bg = None
        self.fore_sizes = (0, 0, 0)
        self.back_sizes = (0, 0, 0)

        with open(path) as f:
            data = json.load(f)
            self.left_fore = pygame.image.load(data["left_fore"]).convert_alpha()
            self.right_fore = pygame.image.load(data["right_fore"]).convert_alpha()
            self.mid_fg = pygame.image.load(data["mid_fore"]).convert_alpha()

            self.left_back = pygame.image.load(data["left_back"]).convert_alpha()
            self.right_back = pygame.image.load(data["right_back"]).convert_alpha()
            self.mid_bg = pygame.image.load(data["mid_back"]).convert_alpha()
            self.update_bar()

    def set_percent(self, percent):
        self.percent = percent
        self.update_bar()

    def update_bar(self):
        lw = self.left_fore.get_width()
        rw = self.right_fore.get_width()
        mw = int((self.width - lw - rw) * self.percent)
        if mw > 0:
            self.fore_sizes = (lw, mw, rw)
            self.mid_fore = pygame.transform.smoothscale(self.mid_fg, (mw, self.mid_fg.get_height()))
        else:
            self.fore_sizes = (lw, 0, rw)

        lbw = self.left_back.get_width()
        rbw = self.right_back.get_width()
        mbw = (self.width - lbw - rbw)
        if mbw > 0:
            self.back_sizes = (lbw, mbw, rbw)
            self.mid_back = pygame.transform.smoothscale(self.mid_bg, (mbw, self.mid_bg.get_height()))
        else:
            self.back_sizes = (lbw, 0, rbw)

    def event(self, event):
        pass

    def lerp(self, v0, v1, t):
        return v0 + t * (v1 - v0)

    def update(self):
        pass

    def render(self, screen):
        pos = self.get_abs_pos()
        if self.left_back is not None:
            screen.blit(self.left_back, pos)
        if self.mid_back is not None and self.back_sizes[1] > 0:
            screen.blit(self.mid_back, (pos[0] + self.back_sizes[0], pos[1]))
        if self.right_back is not None:
            screen.blit(self.right_back, (pos[0] + self.back_sizes[0] + self.back_sizes[1], pos[1]))

        if self.percent <= 0:
            return

        if self.left_fore is not None:
            screen.blit(self.left_fore, pos)
        if self.mid_fore is not None and self.fore_sizes[1] > 0:
            screen.blit(self.mid_fore, (pos[0] + self.fore_sizes[0], pos[1]))
        if self.right_fore is not None:
            screen.blit(self.right_fore, (pos[0] + self.fore_sizes[0] + self.fore_sizes[1], pos[1]))


class Button(Container):
    label = None
    image = None
    width = 0
    height = 0
    callback = None

    def __init__(self, path, width, height, font, label="Button", label_color=(255, 255, 255)):
        Container.__init__(self)
        with open(path) as f:
            data = json.load(f)
            slices = data["slice"]
            image = pygame.image.load(data["image"]).convert_alpha()
            self.image = SliceSprite(image, slicing=(slices["l"], slices["r"], slices["t"], slices["b"]))
        self.pos = (0, 0)
        self.width = width
        self.height = height
        self.image.set_rect((0, 0, self.width, self.height))

        self.label = Label(font, label, label_color)
        self.add_object(self.label)
        self.label.position(10, 8)

    def set_callback(self, callback):
        self.callback = callback

    def event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse = pygame.mouse.get_pos()
            if self.pressed(mouse):
                if self.callback is not None:
                    self.callback()

    def update(self):
        Container.update(self)
        if self.dirty:
            pos = self.get_abs_pos()
            self.image.set_rect((pos[0], pos[1], self.width, self.height))
            self.dirty = False

    def render(self, screen):
        if self.image is not None:
            self.image.render(screen)
        Container.render(self, screen)

    def pressed(self, mouse):
        x, y, w, h = self.image.get_rect()
        rect = pygame.Rect(x, y, w, h)
        if mouse[0] > rect.topleft[0]:
            if mouse[1] > rect.topleft[1]:
                if mouse[0] < rect.bottomright[0]:
                    if mouse[1] < rect.bottomright[1]:
                        return True
                    else: return False
                else: return False
            else: return False
        else: return False

    def position(self, x, y):
        Container.position(self, x, y)
        pos = self.get_abs_pos()
        self.image.set_rect((pos[0], pos[1], self.width, self.height))
