cavefilter
==========

convenience tool for paludis package manager

paludis/cave is very powerful, but sometimes it's annoying to dig through a long list
of packages to update but you just quickly want to select some packages or you have
some blockers and you know best what's good for your system.

Then cave_filter will do a quick and dirty update job for you.
You can use it like an alias to "sync; list update packages; select packages to update; update",  but it's much more convenient'.

There is a config file in "/etc/cave_filter.cfg" or if you wish per user config files
in "~/.config/cave_filter.cfg",  where you can specify which flags should be used by cave for update search and install.

The first usage of cave will be like "cave resume" without the execution flag,  it's for quering packages to update and find issues'.

Then you can select by different strategies your packages,  eg. provide a range or number,
a package prefix or (de-)select all. A \[x\] means it's selected to update, otherwise not.

This script will use a cache file to remember from the last run, which packages you have had deselected.

Also this tool respects a resume file when present and directly starts resuming the update if not userwise specified witl a flag.

Have a look at the cli help for more information for flags to use.
