*grads -a 1.777777778
'reinit'
'reset'
'set background 1'
'c'

nt=571

explist='grass urban evergreen'
modellist='VVM VVMex'
iexp=1
while(iexp<=3)
explab=subwrd(explist, iexp)
imo=1
while(imo<=2)
model=subwrd(modellist, imo)

say model' 'explab

'sdfopen ./data/'explab'_'model'.nc'

'c'

'set x 1'
'set y 1'
'set z 1'
'set t 1 'nt


'set timelab off'
'set grads off'

'set z 1'
*fig tg
'set tlsupp month'
'mul 3 2 1 2  -xwid 2.5 -ywid 1.5 -xint 1 -yint 1.0'
'set vrange 295 335'
'set cmark 0'
'set cthick 10'
'set cstyle 1'
'set ccolor 1'
'd tg'

'off'
'set cmark 0'
'set cthick 10'
'set cstyle 4'
'set ccolor 1'
'd ta'
'draw title TG, Ta(dash) [K]'
'on'

*fig sw
'mul 3 2 2 2  -xwid 2.5 -ywid 1.5 -xint 1 -yint 1.0'
'set vrange -200 1200'
'set ylint 200'
'set cmark 0'
'set cthick 10'
'set cstyle 1'
'set ccolor 1'
'd sw'
'draw title SW [Wm`a-2`n]'

*Page Size = 11 by 6.1875
'set strsiz 0.3'
'set string 1 c 8 0'
'draw string 5.5 5.8 'model

*fig lw
'mul 3 2 3 2  -xwid 2.5 -ywid 1.5 -xint 1 -yint 1.0'
'set t 2 'nt
'set vrange 300 600'
'set ylint 50'
'set cmark 0'
'set cthick 10'
'set cstyle 1'
'set ccolor 1'
'd lw'
'draw title LW [Wm`a-2`n]'

*fig sh
'mul 3 2 1 1  -xwid 2.5 -ywid 1.5 -xint 1 -yint 1.0'
'set vrange -100 600'
'set ylint 100'
'set cmark 0'
'set cthick 10'
'set ccolor 1'
'set cstyle 1'
'd sh'

'off'
'set cmark 0'
'set cthick 10'
'set ccolor 1'
'set cstyle 4'
'off'
'd lh'
'on'
'draw title SH, LH(dash) [Wm`a-2`n]'

*fig gfx
'mul 3 2 2 1 -xwid 2.5 -ywid 1.5 -xint 1 -yint 1.0'
'set vrange -800 200'
'set ylint 200'
'set cmark 0'
'set cthick 10'
'set cstyle 1'
'set ccolor 1'
'd gfx'
'draw title GH [Wm`a-2`n]'

*fig ws
'mul 3 2 3 1  -xwid 2.5 -ywid 1.5 -xint 1 -yint 1.0'
'set vrange -0.2 3.5'
'set ylint 0.5'
'set cmark 0'
'set cthick 10'
'set cstyle 1'
'set ccolor 1'
'd ws'
'draw title WS [ms`a-1`n]'

'gxprint ./fig/tg_'model'_'explab'.pdf'

'close 1'

imo=imo+1
endwhile
iexp=iexp+1
endwhile
