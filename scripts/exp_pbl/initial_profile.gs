'reinit'
'reset'
'set background 1'
'c'

explab='grass'
expex=explab'_good_luck'

'open ../../VVMex/'expex'/vvm.ctl'
nz=99

'set x 1'
'set y 1'
'set z 1 'nz

'set xlopts 1 5 0.2'
'set ylopts 1 5 0.2'

'set grads off'

'mul 1 1 1 1 -xini 1 -xint 2.5 -xwid 4.5 -ywid 6'
'set vrange 298 420'
'set xlint 20'
'set cthick 10'
'set cmark 0'
'set ccolor 1'
'd th'
'draw title Theta [K]'

'mul 2 1 2 1 -xini 1 -xint 2.2 -xwid 3.8 -ywid 6'
'set vrange 0 20'
'set xlint 2'
'set cthick 10'
'set cmark 0'
'set ccolor 1'
'd qv*1e3'
'draw title Qv [g kg`a-1`n]'
'draw ylab [m]'

'set strsiz 0.3'
'set string 1 c 5 0'
'draw string 5.75 8 Homogeneous diurnal boundary layer'

'gxprint ./fig/pbl_initial.pdf'


