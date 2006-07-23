"""
Small custom builders useful for scons-addons
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

__revision__ = "__FILE__ __REVISION__ __DATE__ __DEVELOPER__"

import os, sys, re
import SConsAddons.Util as sca_util
import SConsAddons.EnvironmentBuilder as sca_envbldr
import SCons.Defaults
import SCons.Environment
import SCons.Node.FS
import SCons.Util

def CreateSubst(target, source, env):
   """ Custom builder helpful for creating *-config scripts and just about anything
       else that can be based on substitutability from a map.
      
      The builder works by pulling the variable 'submap' out of the environment
      and then any place in the source where key from the map exists,
      that content is replaced with the value of the key in the dictionary.
      
      Example:
         submap = {
         '@prefix@'                    : my_prefix,
         '@version@'                   : version_str
      }

         my_file = env.ConfigBuilder('file.out','file.in', submap=submap)
         env.AddPostAction (my_file, Chmod('$TARGET', 0644))
         env.Depends(my_file, 'version.h')
   """
   targets = map(lambda x: str(x), target)
   sources = map(lambda x: str(x), source)

   submap = env['submap']

   # Build each target from its source
   for i in range(len(targets)):
      print "Generating config file " + targets[i]
      contents = open(sources[i], 'r').read()

      # Go through the substitution dictionary and modify the contents read in
      # from the source file
      for key, value in submap.items():
         contents = re.sub(re.escape(key), value, contents)

      # Write out the target file with the new contents
      open(targets[0], 'w').write(contents)
      os.chmod(targets[0], 0755)

def registerSubstBuilder(env):
   env["BUILDERS"]["SubstBuilder"] = \
            SCons.Builder.Builder(action=SCons.Action.Action(CreateSubst, 
                                                             varlist=['submap',]))
