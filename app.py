import pygame
import pygame.display
from pygame.locals import *

class App:
    def __init__(self):
        self.bg_color = (0, 0, 0)
        self.screen = None
        self.size = (200, 120)
        self.running = True
        self.clock = pygame.time.Clock()
        self.FPS = 30
        self.objects = list(())
        pygame.init()

    def init_display(self):
        pygame.display.init()

        modes = pygame.display.list_modes(16)
        if not modes:
            print '16-bit not supported'
            modes = pygame.display.list_modes(32)
            if not modes:
                '32-bit not supported either!'
                self.running = False
            else:
                print 'Found resolution: ', modes[0]
                self.size = modes[0]
                self.screen = pygame.display.set_mode(modes[0], pygame.FULLSCREEN, 32)
        else:
            print 'Found resolution: ', modes[0]
            self.size = modes[0]
            self.screen = pygame.display.set_mode(modes[0], pygame.FULLSCREEN, 16)

    def add_object(self, object):
        self.objects.append(object)

    def remove_object(self, object):
        self.objects.remove(object)

    def on_key_down(self, event):
        if event.key == pygame.K_ESCAPE:
            self.running = False

    def process_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            if event.type == pygame.KEYDOWN:
                self.on_key_down(event)
            else:
                for object in self.objects:
                    object.event(event)

    def pre_update(self):
        pass

    def update(self):
        for object in self.objects:
            object.update()

    def post_update(self):
        pass

    def pre_render(self):
        pass

    def render(self):
        self.screen.fill(self.bg_color)
        for object in self.objects:
            object.render(self.screen)

    def post_render(self):
        pass

    def run(self):
        while self.running:
            self.process_events()

            self.pre_render()
            self.update()
            self.post_update()

            self.pre_render()
            self.render()
            self.post_render()

            pygame.display.flip()
            self.clock.tick(self.FPS)

    def set_bg_color(self, color):
        self.bg_color = (color[0], color[1], color[2])
