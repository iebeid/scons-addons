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

import types
import SCons.Errors
import SCons.Util
import os.path

# TODO: Port more standard SCons options over to this interface.
#

def bogus_func():
    pass

class Option:
    """
    Base class for all options.
    An option in our context is:
      - Something(s) that can be set and found
      - Once set(found) has the ability to set an environment with those settings      
    """
    def __init__(self, name, keys, help):
        """
        Create an option
        name - Name of the option
        keys - the name (or names) of the commandline option
        help - Help text about the option object. If different help per key, put help in a list.
        """
        self.name = name
        if not SCons.Util.is_List(keys):
           keys = [keys]        
        self.keys = keys
        self.help = help
        self.verbose = False      # If verbose, then output more information
        
    def startProcess(self):
        """ Called at beginning of processing.  Perform any intialization or notification here. """
        print "Updating ", self.name
        pass
        
    def setInitial(self, optDict):
        """ Given an initial option Dictionary (probably from option file) initialize our data """
        pass
        
    def find(self, env):
        """ 
        Find the option setting (find default).  Called even if option already set.
        env - The current environment
        post: Should store internal rep of the value to use
        """
        pass
    
    def validate(self, env):
        """ Validate the option settings.  This checks to see if there are problems
            with the configured settings.
        """
        pass
    
    def completeProcess(self,env):
        """ Called when processing is complete. """
        pass
    
    def apply(self, env):
        """ Apply the results of the option to the given environment. """
        pass
    
    def getSettings(self):
        """ Return list sequence of ((key,value),(key,value),).
            dict.iteritems() should work.
            Used to save out settings for persistent options.
        """
        assert False, "Please implement a getSettings() method to return settings to save."
        return []
        

class LocalUpdateOption(Option):
    """ Extends the base option to have another method that allows updating of environment locally """
    def __init__(self, name, keys, help):
        Option.__init__(self, name, keys, help)
        
    def updateEnv(self, env, *pa, **kw):
        """ Deprecated. """
        print "DEPRECATED: method LocalUpdateOptions.updateEnv is deprecated. Please call 'apply' instead."
        self.apply(env, *pa, **kw)
    

class PackageOption(LocalUpdateOption):
    """ Base class for options that are used for specifying options for installed software packages. """
    def __init__(self, name, keys, help):
        LocalUpdateOption.__init__(self,name,keys,help)
        self.available = False
        
    def isAvailable(self):
        " Return true if the package is available "
        return self.available
    
    def setAvailable(self, val):
        self.available = val

        
class SimpleOption(Option):
    """
    Implementation of a simple option wrapper.  This is used by Options.Add()
    This Option works for a single option value with a single key (stored internally)
    """
    def __init__(self, name, keys, help, finder, converter, setter, validator):
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
        validator - Function called to validate the option value
                    called with (key, value, environment)
        """
        Option.__init__(self, name, keys, help);
        if None == finder:
            self.finder_cb = None
        elif type(bogus_func) == type(finder):
            self.finder_cb = finder
        else:
            self.finder_cb = lambda key, env: finder
        self.converter_cb = converter
        self.setter_cb = setter
        self.validator_cb = validator
        self.value = None
        
    def setInitial(self, optDict):
        if optDict.has_key(self.keys[0]):
            self.value = optDict[self.keys[0]]

    def find(self, env):
        if None == self.value:     # If not already set by setInitial()
            if self.finder_cb:
                self.value = self.finder_cb(self.keys[0], env)
            else:
                self.value = None    
        
    def validate(self, env):
        """ Validate and convert the option settings """
        # -- convert the values -- #
        if self.converter_cb and self.value:
            try:
                self.value = self.converter_cb(self.value)
            except ValueError, x:
                raise SCons.Errors.UserError, 'Error converting option: %s value:%s\n%s'%(self.keys[0], self.value, x)
            
        # -- validate --- #
        if self.validator_cb and self.value:
            self.validator_cb(self.keys[0], self.value, env)
    
    def apply(self, env):
        env[self.keys[0]] = self.value
    
    def getSettings(self):
        return [(self.keys[0],self.value),]


class BoolOption(Option):
    """
    Implementation of a bool option wrapper. 
    This option wraps a single 'truth' value expressed as a string.
    """
    true_strings  = ('y', 'yes', 'true', 't', '1', 'on' , 'all' )
    false_strings = ('n', 'no', 'false', 'f', '0', 'off', 'none') 
   
    def __init__(self, key, help, default):
        """
        Create a bool option
        key - the name of the commandline option
        help - Help text about the option object
        default - Default truth value
        """
        Option.__init__(self, key, key, "%s (yes|no)"%help);        
        self.value = None
        self.default = default
    
    def textToBool(val):
        """
        Converts strings to True/False depending on the 'truth' expressed by
        the string. If the string can't be converted, the original value
        will be returned.
        """
        if isinstance(val, types.BooleanType):
            return val
        
        lval = string.lower(val)
        if lval in BoolOption.true_strings: return True
        if lval in BoolOption.false_strings: return False
        raise ValueError("Invalid value for boolean option: %s" % val)

    def setInitial(self, optDict):
        if optDict.has_key(self.keys[0]):
            self.value = optDict[self.keys[0]]

    def find(self, env):
        if None == self.value:     # If not already set by setInitial()
            self.value = self.default
    
    def validate(self, env):
        """ Validate and convert the option settings """
        if self.value:
            try:
                self.value = textToBool(self.value)
            except ValueError, x:
                raise SCons.Errors.UserError, 'Error converting option: %s value:%s\n%s'%(self.keys[0], self.value, x)
    
    def apply(self,env):
        env[self.keys[0]] = self.value
    
    def getSettings(self):
        return [(self.keys[0],self.value),]

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
        self.verbose = False        # If true, then we will set all contained options to verbose before processing
        
        if SCons.Util.is_String(files):
           self.files = [ files, ];
        elif (files != None):
           self.files = files;


    def Add(self, key, help="", default=None, validator=None, converter=None, name=None):
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
            name = "unamed_opt_" + str(key)
            
        option = SimpleOption(name, key, help, default, converter, None, validator)

        self.options.append(option)
        
    def AddOption(self, option):
        """ Add a single option object"""
        for k in option.keys:
            if not SCons.Util.is_valid_construction_var(k):
                raise SCons.Errors.UserError, "Illegal Options.AddOption(): opt: '%s' -- key `%s'" % (options.name, option.key)

        self.options.append(option)
     
        
    def GetOption(self, name):
        """ Return the named option or None if not found"""
        for option in self.options:
            if name == option.name:
                return option
        return None

    def Update(self, env, args=None):
        """ Deprecated method of calling Process. """
        self.Process(env,args,applySimple=True)
        
    def Process(self, env, args=None, applySimple=True):
        """
        Process all options within the given environment.
        This will go through all options and will initialize, find, and validate
        them against this environment.
        If applySimple is set true, it will finish off by applying all simple options.
        Update an environment with the option variables.

        env - the environment to update.
        args - the dictionary to get the command line arguments from.
        """

        values = {}
        
        # Setup verbosity
        if self.verbose:
            for option in self.options:
                option.verbose = True

        # first load previous values from file
        for filename in self.files:
           if os.path.exists(filename):
              execfile(filename, values)
        
        # Next over-ride those with command line args
        if args is None:
            args = self.args
        values.update(args)
        
        # Process each option in order
        for option in self.options:
            option.startProcess()         # Start processing
            option.setInitial(values)     # Set initial values
            option.find(env)              # Find values if needed
            option.validate(env)          # Validate the settings
            option.completeProcess(env)   # Signal processing completed
    
        # Apply options if requested
        if True == applySimple:
            self.Apply(env, allowedTypes=(SimpleOption,))
    

    def Apply(self, env, all=False, allowedTypes=(), allowedNames=()):
        """ Apply options from this option group to the given environment.
            all - If set true, then applies all options.
            allowedTypes - If set, it is a list of option types that will be applied.
            allowedNames - If set, it is a list of option names that will be applied.
            note: if both are set, then either must be true.
        """
        #print "Options.Apply: %s %s %s"%(all, allowedTypes, allowedNames)
        for option in self.options:
            #print "Checking: ", option.name
            if (True == all) or (isinstance(option, allowedTypes)) or (option.name in allowedNames):
                #print "    Passed, applying."
                option.apply(env)

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
                # For each option and each key
                key_value_list = []
                for o in self.options:
                    key_value_list.extend(o.getSettings())                    
                for (key,value) in key_value_list:
                    if None != value:
                        try:
                            eval(repr(value))
                        except:
                            # Convert stuff that has a repr that cannon be evaled to string
                            value = SCons.Util.to_string(value)                        
                        fh.write('%s = %s\n' % (key, repr(value)))
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

        help_text = "\nOption Modules\n"

        if sort:
            options = self.options[:]
            options.sort(lambda x,y,func=sort: func(x.key[0],y.key[0]))
        else:
            options = self.options

        key_list = []
        for o in options:
            key_list.extend(o.keys)
                
        max_key_len = max([len(k) for k in key_list])             # Get max key for spacing
        
        for option in options:
            for ki in range(len(option.keys)):
                k = option.keys[ki]
                k_help = option.help
                if SCons.Util.is_List(option.help):
                    k_help = option.help[ki]    
                help_text = help_text + '   %*s: %s' % (max_key_len, k, k_help)

                if env.has_key(k):
                    help_text = help_text + '  val: [%s]\n'%env.subst('${%s}'%k)
                else:
                    help_text = help_text + '  val: [None]\n'

        return help_text

