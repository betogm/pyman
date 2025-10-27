# -*- coding: utf-8 -*-
#
# PyMan - Python HTTP Request Executor
# Author: Huberto Gastal Mayer (hubertogm@gmail.com)
# License: GPLv3 (https://www.gnu.org/licenses/gpl-3.0.html)
# Project: PyMan - A CLI tool for executing HTTP request collections defined in YAML
#

import random
import string
import time

"""
Helper functions inspired by Postman (pm.globals, etc.)
In our scripts, this will be accessed as 'pm'.
Ex: {{pm.random_int(1, 10)}}
"""

class PyManHelpers:
    """
    Contains a set of utility functions that can be injected
    into pre/post scripts and used in variable substitutions.
    """
    
    def __init__(self):
        # A place to store dynamic variables if needed (like pm.variables)
        self._variables = {}

    def set_variable(self, key, value):
        """Defines a dynamic variable."""
        self._variables[key] = value

    def get_variable(self, key):
        """Gets a dynamic variable."""
        return self._variables.get(key)

    # --- Dynamic Functions ({{pm.helper()}}) ---

    def timestamp(self):
        """Returns the current Unix timestamp in seconds."""
        return int(time.time())

    def random_int(self, min_val=0, max_val=1000):
        """Returns a random integer within the range."""
        return random.randint(int(min_val), int(max_val))

    def random_choice(self, *choices):
        """Returns a random choice from the provided arguments."""
        if not choices:
            return ""
        return random.choice(choices)

    def random_chars(self, length=10, char_set=string.ascii_letters + string.digits):
        """Returns a random string from the character set."""
        length = int(length)
        return ''.join(random.choice(char_set) for _ in range(length))

    def random_adjective(self):
        """Returns a random adjective."""
        adjectives = [
            'quick', 'blue', 'slow', 'bright', 'dark', 'hot',
            'cold', 'big', 'small', 'new', 'old', 'good', 'bad'
        ]
        return random.choice(adjectives)

    def random_noun(self):
        """Returns a random noun."""
        nouns = [
            'car', 'house', 'cat', 'dog', 'book', 'tree',
            'computer', 'phone', 'river', 'sun', 'moon'
        ]
        return random.choice(nouns)
        
    def random_music_genre(self):
        """Returns a random music genre."""
        genres = [
            'Rock', 'Pop', 'Jazz', 'Classical', 'Hip Hop', 'Electronic',
            'Samba', 'Bossa Nova', 'Funk', 'Reggae', 'Metal'
        ]
        return random.choice(genres)

    def random_uuid(self):
        """Generates a v4 UUID (requires 'import uuid' at the top of this file)."""
        try:
            import uuid
            return str(uuid.uuid4())
        except ImportError:
            # Simple fallback if the uuid module is not available (unlikely)
            return self.random_chars(8) + '-' + self.random_chars(4) + '-' + \
                   self.random_chars(4) + '-' + self.random_chars(12)

# End of PyManHelpers class