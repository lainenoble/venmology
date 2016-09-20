def process_text(self,text):

    self.stopwords_lower_=set(map(str.lower,self.stopwords))
    
    d={} #dictionary whose keys are words in lowercase
    # and whose values are dictionaries
    # with keys case variations of the word and values count of the variation
    
    flags = (re.UNICODE if sys.version < '3' and type(text) is unicode
                 else 0)
    regexp = self.regexp if self.regexp is not None else r"\w[\w']+"
    for word in re.findall(regexp, text, flags=flags):
            if word.isdigit():
                continue

            word_lower = word.lower()
            if word_lower in self.stopwords_lower_:
                continue
            
            # Look in lowercase dict.
            try:
                d2 = d[word_lower] #has a case variation of this word already appeared?
            except KeyError:
                d2 = {}
                d[word_lower] = d2 #if not, add it as a key in d, with value empty dict

            # Look in any case dict.
            d2[word] = d2.get(word, 0) + 1 #has *this* case variation appeared?
            # if so, increment the count; if not, add it as a key in the inner dict with value 1
            
    # merge plurals into the singular count (simple cases only)
    for key in list(d.keys()):
        if key.endswith('s'):
            key_singular = key[:-1]
            if key_singular in d:
                dict_plural = d[key]
                dict_singular = d[key_singular]
                for word, count in dict_plural.items():
                    singular = word[:-1]
                    dict_singular[singular] = dict_singular.get(singular, 0) + count
                del d[key]
                
    d3={}
    for d2 in d.values():
        # Get the most popular case variation
        first = max(d2.items(),key=item1)[0]
        d3[first] = sum(d2.values())
    
    return d3 #a dict with keys [words with most popular case variation]
    #and values count of that word, including all case variations
    
def generate_from_frequencies(self, frequencies):
        """Create a word_cloud from words and frequencies.
        Parameters
        ----------
        frequencies : array of tuples
            A tuple contains the word and its frequency (count).
        """
        
        # make sure frequencies are sorted and normalized
        frequencies = sorted(frequencies, key=item1, reverse=True)
        frequencies = frequencies[:self.max_words]
        # largest entry will be 1
        max_frequency = float(frequencies[0][1])

        frequencies = [(word, freq / max_frequency) for word, freq in frequencies]

        self.words_ = frequencies

        if self.random_state is not None:
            random_state = self.random_state
        else:
            random_state = Random()

        if len(frequencies) <= 0:
            print("We need at least 1 word to plot a word cloud, got %d."
                  % len(frequencies))
    
        if self.mask is not None:
            mask = self.mask
            width = mask.shape[1]
            height = mask.shape[0]
            if mask.dtype.kind == 'f':
                warnings.warn("mask image should be unsigned byte between 0 and"
                              " 255. Got a float array")
            if mask.ndim == 2:
                boolean_mask = mask == 255
            elif mask.ndim == 3:
                # if all channels are white, mask out
                boolean_mask = np.all(mask[:, :, :3] == 255, axis=-1)
            else:
                raise ValueError("Got mask of invalid shape: %s" % str(mask.shape))
        else:
            boolean_mask = None
            height, width = self.height, self.width
        occupancy = IntegralOccupancyMap(height, width, boolean_mask)
        
        # create image
        img_grey = Image.new("L", (width, height))
        draw = ImageDraw.Draw(img_grey)
        img_array = np.asarray(img_grey)
        font_sizes, positions, orientations, colors = [], [], [], []

        font_size = self.max_font_size
        last_freq = 1.

        # start drawing grey image
        for word, freq in frequencies:
            # select the font size
            rs = self.relative_scaling
            if rs != 0:
                font_size = int(round((rs * (freq / float(last_freq)) + (1 - rs)) * font_size))
            while True:
                # try to find a position
                font = ImageFont.truetype(self.font_path, font_size)
                # transpose font optionally
                if random_state.random() < self.prefer_horizontal:
                    orientation = None
                else:
                    orientation = Image.ROTATE_90
                transposed_font = ImageFont.TransposedFont(font,
                                                           orientation=orientation)
                # get size of resulting text
                box_size = draw.textsize(word, font=transposed_font)
                # find possible places using integral image:
                result = occupancy.sample_position(box_size[1] + self.margin,
                                                   box_size[0] + self.margin,
                                                   random_state)
                if result is not None or font_size == 0:
                    break
                # if we didn't find a place, make font smaller
                font_size -= self.font_step

            if font_size < self.min_font_size:
                # we were unable to draw any more
                break

            x, y = np.array(result) + self.margin // 2
            # actually draw the text
            draw.text((y, x), word, fill="white", font=transposed_font)
            positions.append((x, y))
            orientations.append(orientation)
            font_sizes.append(font_size)
            colors.append(self.color_func(word, font_size=font_size,
                                          position=(x, y),
                                          orientation=orientation,
                                          random_state=random_state,
                                          font_path=self.font_path))
            # recompute integral image
            if self.mask is None:
                img_array = np.asarray(img_grey)
            else:
                img_array = np.asarray(img_grey) + boolean_mask
            # recompute bottom right
            # the order of the cumsum's is important for speed ?!
            occupancy.update(img_array, x, y)
            last_freq = freq

        self.layout_ = list(zip(frequencies, font_sizes, positions, orientations, colors))
        return self
        
    def _check_generated(self):
        """Check if ``layout_`` was computed, otherwise raise error."""
        if not hasattr(self, "layout_"):
            raise ValueError("WordCloud has not been calculated, call generate first.")

    def to_image(self):
        self._check_generated()
        if self.mask is not None:
            width = self.mask.shape[1]
            height = self.mask.shape[0]
        else:
            height, width = self.height, self.width

        img = Image.new(self.mode, (int(width * self.scale), int(height * self.scale)),
                        self.background_color)
        draw = ImageDraw.Draw(img)
        for (word, count), font_size, position, orientation, color in self.layout_:
            font = ImageFont.truetype(self.font_path, int(font_size * self.scale))
            transposed_font = ImageFont.TransposedFont(font,
                                                       orientation=orientation)
            pos = (int(position[1] * self.scale), int(position[0] * self.scale))
            draw.text(pos, word, fill=color, font=transposed_font)
        return img

    def recolor(self, random_state=None, color_func=None):
        """Recolor existing layout.
        Applying a new coloring is much faster than generating the whole wordcloud.
        Parameters
        ----------
        random_state : RandomState, int, or None, default=None
            If not None, a fixed random state is used. If an int is given, this
            is used as seed for a random.Random state.
        color_func : function or None, default=None
            Function to generate new color from word count, font size, position
            and orientation.  If None, self.color_func is used.
        Returns
        -------
        self
        """
        if isinstance(random_state, int):
            random_state = Random(random_state)
        self._check_generated()

        if color_func is None:
            color_func = self.color_func
        self.layout_ = [(word_freq, font_size, position, orientation,
                         color_func(word=word_freq[0], font_size=font_size,
                                    position=position, orientation=orientation,
                                    random_state=random_state, font_path=self.font_path))
                        for word_freq, font_size, position, orientation, _ in self.layout_]
        return self

    def to_file(self, filename):
        """Export to image file.
        Parameters
        ----------
        filename : string
            Location to write to.
        Returns
        -------
        self
        """

        img = self.to_image()
        img.save(filename)
        return self