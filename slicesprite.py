import pygame

class SliceSprite(pygame.sprite.Sprite):
    """
    SliceSprite extends pygame.sprite.Sprite to allow for 9-slicing of its contents.
    Slicing of its image property is set using a slicing tuple (left, right, top, bottom).
    Values for (left, right, top, bottom) are distances from the image edges.
    """
    width_error = ValueError("SliceSprite width cannot be less than (left + right) slicing")
    height_error = ValueError("SliceSprite height cannot be less than (top + bottom) slicing")

    def __init__(self, image, slicing=(0, 0, 0, 0)):
        """
        Creates a SliceSprite object.
        _sliced_image is generated in _generate_slices() only when _regenerate_slices is True.
        This avoids recomputing the sliced image whenever each SliceSprite parameter is changed
        unless absolutely necessary! Additionally, _rect does not have direct @property access
        since updating properties of the rect would not be trigger _regenerate_slices.

        Args:
            image (pygame.Surface): the original surface to be sliced
            slicing (tuple(left, right, top, bottom): the 9-slicing margins relative to image edges
        """
        pygame.sprite.Sprite.__init__(self)
        self._image = image
        self._sliced_image = None
        self._rect = self.image.get_rect()
        self._slicing = slicing
        self._regenerate_slices = True

    @property
    def image(self):
        return self._image

    @image.setter
    def image(self, new_image):
        self._image = new_image
        self._regenerate_slices = True

    @property
    def width(self):
        return self._rect.width

    @width.setter
    def width(self, new_width):
        self._rect.width = new_width
        self._regenerate_slices = True

    @property
    def height(self):
        return self._rect.height

    @height.setter
    def height(self, new_height):
        self._rect.height = new_height
        self._regenerate_slices = True

    @property
    def x(self):
        return self._rect.x

    @x.setter
    def x(self, new_x):
        self._rect.x = new_x
        self._regenerate_slices = True

    @property
    def y(self):
        return self._rect.y

    @y.setter
    def y(self, new_y):
        self._rect.y = new_y
        self._regenerate_slices = True

    @property
    def slicing(self):
        return self._slicing

    @slicing.setter
    def slicing(self, new_slicing=(0, 0, 0, 0)):
        self._slicing = new_slicing
        self._regenerate_slices = True

    def get_rect(self):
        return self._rect

    def set_rect(self, new_rect):
        self._rect = new_rect
        self._regenerate_slices = True

    def _generate_slices(self):
        """
        Internal method required to generate _sliced_image property.
        This first creates nine subsurfaces of the original image (corners, edges, and center).
        Next, each subsurface is appropriately scaled using pygame.transform.smoothscale.
        Finally, each subsurface is translated in "relative coordinates."
        Raises appropriate errors if rect cannot fit the center of the original image.
        """
        num_slices = 9
        x, y, w, h = self._image.get_rect()
        l, r, t, b = self._slicing
        mw = w - l - r
        mh = h - t - b
        wr = w - r
        hb = h - b

        rect_data = [
            (0, 0, l, t), (l, 0, mw, t), (wr, 0, r, t),
            (0, t, l, mh), (l, t, mw, mh), (wr, t, r, mh),
            (0, hb, l, b), (l, hb, mw, b), (wr, hb, r, b),
        ]

        x, y, w, h = self._rect
        mw = w - l - r
        mh = h - t - b
        if mw < 0: raise SliceSprite.width_error
        if mh < 0: raise SliceSprite.height_error

        scales = [
            (l, t), (mw, t), (r, t),
            (l, mh), (mw, mh), (r, mh),
            (l, b), (mw, b), (r, b),
        ]

        translations = [
            (0, 0), (l, 0), (l + mw, 0),
            (0, t), (l, t), (l + mw, t),
            (0, t + mh), (l, t + mh), (l + mw, t + mh),
        ]

        self._sliced_image = pygame.Surface((w, h), pygame.SRCALPHA, 32)
        for i in range(num_slices):
            rect = pygame.rect.Rect(rect_data[i])
            surf_slice = self.image.subsurface(rect)
            stretched_slice = pygame.transform.smoothscale(surf_slice, scales[i])
            self._sliced_image.blit(stretched_slice, translations[i])

    def event(self, event):
        pass

    def update(self):
        pass

    def render(self, surface):
        """
        Draws the SliceSprite onto the desired surface.
        Calls _generate_slices only at draw time only if necessary.
        Note that the final translation occurs here in "absolute coordinates."

        Args:
            surface (pygame.Surface): the parent surface for blitting SliceSprite
        """
        x, y, w, h, = self._rect
        if self._regenerate_slices:
            self._generate_slices()
            self._regenerate_slices = False
        surface.blit(self._sliced_image, (x, y))