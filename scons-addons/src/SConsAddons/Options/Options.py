"""SConsAddons.Options.Options

Defines options extension for supporting modular options.
"""

#
# __COPYRIGHT__
#
# This file is part of scons-addons.
#
# Scons-addons is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Scons-addons is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with scons-addons; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
# Based on scons Options.py code
#
# Copyright Steven Knight
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY
# KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
# WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

__revision__ = "__FILE__ __REVISION__ __DATE__ __DEVELOPER__"

import SCons.Errors
import SCons.Util
import os.path

def bogus_func():
    pass

class Option:
    """
    Base class for all options.
    """
    def __init__(self, name, key, help):
        """
        Create an option
        name - Name of the option
        key - the name of the commandline option
        help - Help text about the option object
        """
        self.name = name
        self.key = key
        self.help = help
        
    def setInitial(self, optDict):
        """ Given an initial option Dictionary (probably from option file) initialize our data """
        pass
        
    def find(self, env):
        """ 
        Find the option setting (find default).  Only called if the user does not specify option.
        env - The current environment
        post: Should store internal rep of the value to use
        """
        pass
    
    def convert(self):
        """ Convert the value """
        pass
    
    def set(self, env):
        """ Set the value(s) in the environment """
        pass
    
    def validate(self, env):
        """ Validate the option settings """
        pass

class LocalUpdateOption(Option):
    """ Extends the base option to have another method that allows updating of environment locally """
    def __init__(self, name, key, help):
        Option.__init__(self, name, key, help)
        
    def updateEnv(self, env):
        """ Update the passed environment with full settings for the option """
        pass

        
class SimpleOption(Option):
    """
    Implementation of a simple option wrapper.  This is used by Options.Add()
    This Option works for a single option value with a single key (stored internally)
    """
    def __init__(self, name, key, help, finder, converter, setter, validater):
        """
        Create an option
        name - Name of the option
        key - the name of the commandline option
        help - Help text about the option object
        finder - Function for searching for value or default value.
                 If method, called with (key, environment)
        converter - option function that is called to convert the options's value before
                    putting in the environment
        setter - Method called to set/generate the environment
        validater - Function called to validate the option value
                    called with (key, value, environment)
        """
        Option.__init__(self, name, key, help);
        if None == finder:
            self.finder_cb = None
        elif type(bogus_func) == type(finder):
            self.finder_cb = finder
        else:
            self.finder_cb = lambda key, env: finder
        self.converter_cb = converter
        self.setter_cb = setter
        self.validater_cb = validater
        self.value = None
        
    def setInitial(self, optDict):
        if optDict.has_key(self.key):
            self.value = optDict[self.key]

    def find(self, env):
        if None == self.value:     # If not already set by setInitial()
            if self.finder_cb:
                self.value = self.finder_cb(self.key, env)
            else:
                self.value = None
    
    def convert(self):
        """ Convert the value """
        if self.converter_cb and self.value:
            try:
                self.value = self.converter_cb(self.value)
            except ValueError, x:
                raise SCons.Errors.UserError, 'Error converting option: %s value:%s\n%s'%(self.key, self.value, x)
    
    def set(self, env):
        """ Set the value(s) in the environment """
        if self.value:
            env[self.key] = self.value
    
    def validate(self, env):
        """ Validate the option settings """
        if self.validater_cb and self.value:
            self.validater_cb(self.key, self.value, env)
        
    

class Options:
    """
    Holds all the options, updates the environment with the variables,
    and renders the help text.
    """
    def __init__(self, files=None, args={}):
        """
        files - [optional] List of option configuration files to load
            (backward compatibility) If a single string is passed it is 
                                     automatically placed in a file list
        """

        self.unique_id = 0          # Id used to create unique names
        self.options = []           # List of option objects managed
        self.files = []             # Options files to load
        self.args = args            # Set the default args from command line
        
        if SCons.Util.is_String(files):
           self.files = [ files, ];
        elif (files != None):
           self.files = files;


    def Add(self, key, help="", finder=None, validater=None, converter=None, name=None):
        """
        Add an option.

        Backwards compatible with standard scons options.
        
        key - the name of the variable
        help - optional help text for the options
        default - optional default value
        validater - optional function that is called to validate the option's value
                    Called with (key, value, environment)
        converter - optional function that is called to convert the option's value before
                    putting it in the environment.
        """

        if not SCons.Util.is_valid_construction_var(key):
            raise SCons.Errors.UserError, "Illegal Options.Add() key `%s'" % key

        if None == name:
            self.unique_id = self.unique_id + 1
            name = "Unamed_" + str(self.unique_id)
            
        option = SimpleOption(name, key, help, finder, converter, None, validater)

        self.options.append(option)
        
    def AddOption(self, option):
        """ Add a single option object"""
        if not SCons.Util.is_valid_construction_var(option.key):
            raise SCons.Errors.UserError, "Illegal Options.AddOption(): opt: '%s' -- key `%s'" % (options.name, option.key)

        self.options.append(option)
     
        
    def GetOption(self, name):
        """ Return the named option or None if not found"""
        for option in self.options:
            if name == option.name:
                return option
        return None

    def Update(self, env, args=None):
        """
        Update an environment with the option variables.

        env - the environment to update.
        args - the dictionary to get the command line arguments from.
        """

        values = {}

        # first load previous values from file
        for filename in self.files:
           if os.path.exists(filename):
              execfile(filename, values)
        
        # Next over-ride those with command line args
        if args is None:
            args = self.args
        values.update(args)
        
        # Process each option in order
        # - Set intial value
        # - Find new value if needed
        # - Convert the value
        # - Set the environment
        # - Validate the setting
        for option in self.options:
            option.setInitial(values)
            option.find(env)
            option.convert()
            option.set(env)
            option.validate(env)
    

    def Save(self, filename, env):
        """
        Saves all the options in the given file.  This file can
        then be used to load the options next run.  This can be used
        to create an option cache file.

        filename - Name of the file to save into
        env - the environment get the option values from
        """

        # Create the file and write out the header
        try:
            fh = open(filename, 'w')

            try:
                # Make an assignment in the file for each option within the environment
                # that was assigned a value other than the default.
                for option in self.options:
                    try:
                        value = env[option.key]
                        try:
                            eval(repr(value))
                        except:
                            # Convert stuff that has a repr that cannon be evaled to string
                            value = SCons.Util.to_string(value)
                        
                        fh.write('%s = %s\n' % (option.key, repr(value)))
                    except KeyError:
                        pass
            finally:
                fh.close()

        except IOError, x:
            raise SCons.Errors.UserError, 'Error writing options to file: %s\n%s' % (filename, x)

    def GenerateHelpText(self, env, sort=None):
        """
        Generate the help text for the options.

        env - an environment that is used to get the current values of the options.
        sort - A sort method to use
        """

        help_text = ""

        if sort:
            options = self.options[:]
            options.sort(lambda x,y,func=sort: func(x.key,y.key))
        else:
            options = self.options
            
        for option in options:
            help_text = help_text + '\n%s: %s\n'%(option.key, option.help)
            if env.has_key(option.key):
                help_text = help_text + '    actual: %s\n'%env.subst('${%s}'%option.key)
            else:
                help_text = help_text + '    actual: None\n'

        return help_text

