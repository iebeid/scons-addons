"""
Variants module.  Currently this is just a place to dump
common code used for variant handling.
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


class VariantsHelper(object):
   """ Helper class for managing builds using variants and some standard conventions.
       Note: This class may not be fully general as it is setup to meet some conventions
       that I have found helpful but not necessarily what everyone else may want.
       Also note that the class may end up feeling rather monolithic.  Once again,
       this is simply because it is trying to reuse code across multiple builds.
       
       variantKeys - List of default variant keys to use.  Valid values include:
          type - runtime type (debug,optimize,hybrid)
          libtype - shared,static
          arch - ia32, x64, ppc, ppc64, etc
   """

   def __init__(self, variantKeys=["type","libtype","arch"]):
      
      # List of variants that we are using.
      # - variants[key] - [[option_list,], is alternative]
      self.variants = {}
      self.fillDefaultVariants(variantKeys)
      
      
   def fillDefaultVariants(self, varKeys):
      """ Fill the variants variable with default allowable settings. """
      if "type" in varKeys:
         self.variants["type"] = [["debug","optimized"], True]
         if sca_util.GetPlatform() == "win32":
            self.variants["type"][0].append("hybrid")
      
      if "libtype" in varKeys:
         self.variants["libtype"] = [["shared","static"], False]
      
      if "arch" in varKeys:
         valid_archs = sca_envbldr.detectValidArchs()
         if len(valid_archs) == 0:
            valid_archs = ["default"]
         print "Valid archs: ", valid_archs
         self.variants["arch"] = [valid_archs[:], True]

   # ---- Command-line option processing ---- #
   def addOptions(self, opts):
      """ The VariantHelper has support for adding command line options to an
          option processing object.  This object has to be an instance
          of SConsAddons.Options.   
          The key for the options is the variant 'var_' + key
      """
      import SConsAddons.Options as sca_opts      
      assert isinstance(opts, sca_opts.Options)
      
      known_help_text = {"type":"Types of tun-times to build.",
                         "libtype":"Library types to build.",
                         "arch":"Target processor architectures to build."}

      opts.AddOption(sca_opts.SeparatorOption("\nVariant Helper Options"))      
      
      var_keys = self.variants.keys()
      var_keys.sort()
      for key in var_keys:
         option_key_name = 'var_' + key
         option_help = known_help_text.get(key,"Variant option")
         option_allowed = self.variants[key][0][:]
         opts.Add(sca_opts.ListOption(option_key_name,option_help,
                                      option_allowed,option_allowed))      
   
   def readOptions(self, optEnv):
      """ Read the processed options from the given environment. """
      # For each key, if found in environment, copy the list over to the variant
      var_keys = self.variants.keys()
      for key in var_keys:         
         opt_key_name = "var_" + key
         if optEnv.has_key(opt_key_name):
            print "key: %s  val: %s"%(key,optEnv[opt_key_name])
            self.variants[key][0] = optEnv[opt_key_name][:]



def zipVariants(variantMap):
   """ This method takes a map of variants and items within each variant and returns
       a list of all combinations of ways that the variants can be combined.

       The input format is:
       { key : ([option_list,], is_alternative), }
       - option_list is a list of all items for this variant.
       - is_alternative is a flag saying wether we just need to choose one item or if all
         items can be in the same variant combination

       The return format is:         
       [ {"var":"option", "var2":["op1","op2"]}, .. }
       
       Each entry in the list is a dictionary that fully specfies a combination of
       variant keys and associated items.
       
       Usage:
         # Define the variants to use   
         # - variant[key] - ([option_list,], is alternative)
         variants = {}
         variants["type"]    = (common_env["types"], True)
         variants["libtype"] = (common_env["libtypes"], False)
         variants["arch"]    = (common_env["archs"], True)
   
         # Return list of combos
         # [ {"var":"option", "var2":["op1","op2"], .. }
         var_combos = zipVariants(variants)
    """
          
   # List of (key,[varlist,])
   alt_items = [ (i[0],i[1][0]) for i in variantMap.iteritems() if i[1][1] == True]
   always_items = [ (i[0],i[1][0]) for i in variantMap.iteritems() if i[1][1] == False]
   assert len(alt_items) + len(always_items) == len(variantMap)
   
   alt_item_sizes = [len(i[1]) for i in alt_items]    # Length of the alt lists
   
   # Build up list of
   # [ (key,'option"), (key2,"option"), ...]
   cur_combos=[[]]
   for variant in alt_items:
      new_combos = []
      variant_key = variant[0]
      option_list = variant[1]
      for option in option_list:
         for i in cur_combos:
            new_combos.append(i+[(variant_key,option)])
      cur_combos = new_combos
   
   #print cur_combos
   
   # Now turn the list of combo lists into a list of
   # combo dictionaries
   ret_combos = []
   for c in cur_combos:
      combo = {}
      for i in c:
         combo[i[0]] = i[1]
      for i in always_items:
         combo[i[0]] = i[1]
      ret_combos.append(combo)

   #import pprint
   #pprint.pprint(ret_combos)
   
   return ret_combos

   