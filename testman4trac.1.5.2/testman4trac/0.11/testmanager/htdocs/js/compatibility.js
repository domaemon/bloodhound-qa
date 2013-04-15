﻿/* -*- coding: utf-8 -*-
#
# Copyright (C) 2010-2012 Roberto Longobardi
# 
# This file is part of the Test Manager plugin for Trac.
# 
# The Test Manager plugin for Trac is free software: you can 
# redistribute it and/or modify it under the terms of the GNU 
# General Public License as published by the Free Software Foundation, 
# either version 3 of the License, or (at your option) any later 
# version.
# 
# The Test Manager plugin for Trac is distributed in the hope that it 
# will be useful, but WITHOUT ANY WARRANTY; without even the implied 
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  
# See the GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with the Test Manager plugin for Trac. See the file LICENSE.txt. 
# If not, see <http://www.gnu.org/licenses/>.
#
*/

/******************************************************/
/**              Compatibility layer                  */
/******************************************************/


function expandCollapseSection(nodeId) {
    /* In Trac 0.11 we must handle sections explicitly */
    /* $('#'+nodeId).toggleClass('collapsed'); */
	(function($) {
			        $('#'+nodeId).toggleClass('collapsed');
			    })(jQuery_testmanager);	
}

function _(str) {
	return str;
}
