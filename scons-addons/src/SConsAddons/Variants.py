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
