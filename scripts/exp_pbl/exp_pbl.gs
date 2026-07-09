*grads -a 1.777777778 -blcx exp_pbl.gs
'reinit'
'set cachesf 1000000'
'reset'
'set background 1'
'c'

explab='grass'
explab='urban'
explab='evergreen'

model='VVM'
model='VVMex'

nt=721
nt=571
iz0=1
iz1=16
inthr=3
say model' 'explab

'sdfopen ./data/'explab'_VVMex.nc'
'sdfopen ./data/'explab'_VVM.nc'
'sdfopen ./data/'explab'_l2.nc'

**** --- fig error
'c'
'set x 1'
'set y 1'
'set z 1'
'set t 1 'nt
'set grads off'
'set timelab off'
'mul 1 1 1 1 -xint 1 -xwid 4.5 -ywid 4'
'set vrange 0 8e-4'
'd thbar_l2.3'
'draw title relative L2_norm (theta_bar)'
'gxprint ./fig/ERROR_thbar_'explab'.pdf'
pull c

**** --- fig 2 --
'c'
'mul 2 1 1 1 -xint 1 -xwid 4.5 -ywid 4'
'set vrange 298 316'
'set grads off'
'set timelab off'

'set rgb 81 0 0 0'
'set rgb 82 17 119 51'
'set rgb 83 136 204 138'
'set rgb 84 221 204 119'
'set rgb 85 204 102 119'
'set rgb 86 170 68 153'
'set rgb 87 100 100 100'

'set t 1'
'set x 1'
'set y 1'
'set z 'iz0' 'iz1
num=7
tlist='05 06 09 12 15 18 21'
clist='81 82 83 84 85 86 87'
slist=' 1  1  1  1  1  4  1'

inum=1
while(inum<=num)
if(inum=1); 'on'; else; 'off'; endif
hr=subwrd(tlist,inum)
cnum=subwrd(clist,inum)
snum=subwrd(slist,inum)
say inum' 'hr'Z 'cnum' 'snum' 'model
'set time 'hr'Z'
'set cthick 10'
'set cmark 0'
'set cstyle 'snum
'set ccolor 'cnum
if (model='VVM'); 'd thbar.2'; endif
if (model='VVMex'); 'd thbar.1'; endif
inum=inum+1
endwhile

'legend tl 'num' 5 10 'tlist' 'clist' 'slist

*X Limits = 0.752 to 5.252
*Y Limits = 0.8 to 4.8
** 'set strsiz 0.2'
** 'set string 1 bl 5 0'
** 'draw string 0.752 5.0 (a) 'model
** 'set string 1 br 5 0'
** 'draw string 5.252 5.0 'explab
'draw title (a) 'model' / 'explab


'set strsiz 0.2'
'set string 1 tc 5 0'
'draw string 3.002 0.5 THBAR [K]'

'mul 2 1 2 1 -xint 1 -xwid 4.5 -ywid 4'
'set tlsupp month'
'set x 1'
'set y 1'
'set t 1 'nt
'set z 'iz0
'define thbvvmex0=thbar.1'
'define thbvvm0=thbar.2'

'on'
'set z 'iz0' 'iz1
'color 1 15 2 -gxout shaded -kind (255,255,255,0)-(0)->grainbow'
if (model='VVM')
  'd qcbar.2*1e6'
else
  'd qcbar.1*1e6'
endif
'set cthick 5'
'xcbar 6.4 8.5 4.5 4.7'
'set strsiz 0.15'
'set string 1 tl 5 0'
'draw string 6.4 4.2 'model' qc'
'draw string 6.4 3.9 [10`a-6`n kg/kg]'


'off'
'set gxout contour'
'set clevs 0'
'set clab off'
'set cthick 10'
'set ccolor 1'
'set cstyle 1'
'd thbar.1-thbvvmex0-0.5'

'off'
'set gxout contour'
'set clevs 0'
'set clab off'
'set cthick 10'
'set ccolor 1'
'set cstyle 4'
'd thbar.2-thbvvm0-0.5'

'legend tr 2 5 10 VVMex VVM 1 1 1 4'
*X Limits = 6.252 to 10.752
*Y Limits = 0.8 to 4.8
** 'set strsiz 0.2'
** 'set string 1 bl 5 0'
** 'draw string 6.252 5 (b) pbl height'
** 'set string 1 br 5 0'
** 'draw string 10.762 5 'explab

'draw title (b) PBL height / 'explab

'draw ylab [m]'

'gxprint ./fig/tg2_'model'_'explab'.pdf'
