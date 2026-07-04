*grads -a 1.777777778 -blcx exp_pbl.gs
'reinit'
'reset'
'set background 1'
'c'

explab='grass'
*explab='urban'
*explab='evergreen'

exp0='pbl_'explab'_aaron_dz200'
expex=explab'_good_luck'

model='VVM'
*model='VVMex'

nt=721
iz0=1
iz1=16
inthr=3
say model' 'explab

'open ../../gpu/'expex'/vvm.ctl'
'open ../../cpu/'exp0'/gs_ctl_files/dynamic.ctl'
'open ../../cpu/'exp0'/gs_ctl_files/thermodynamic.ctl'
'open ../../cpu/'exp0'/gs_ctl_files/surface.ctl'
'open ../../cpu/'exp0'/gs_ctl_files/radiation.ctl'
'open ../../cpu/'exp0'/gs_ctl_files/landsurface.ctl'

'set x 1'
'set y 1'
'set z 'iz0' 'iz1
'define wei=rhobar*(lev(z=2)-lev(z=1))'

'set x 1'
'set y 1'
'set z 'iz0' 'iz1
'set t 1 last'
'define thbvvm=aave(th.3,x=1,x=128,y=1,y=128)'
'define thbvvmex=aave(th.1,x=1,x=128,y=1,y=128)'

'set z 'iz0
'define thbvvm0=thbvvm'
'define thbvvmex0=thbvvmex'


'set x 1'
'set y 1'
'set z 1'
'define a=sqrt(mean(pow((thbvvmex-thbvvm)*wei,2),z='iz0',z='iz1'))'
'define b=sqrt(mean(pow(thbvvm*wei,2),z='iz0',z='iz1'))'
'define therr=a/maskout(b,b>0.000001)'


**** --- fig error
'c'
'set x 1'
'set y 1'
'set z 1'
'set t 1 last'
'set grads off'
'set timelab off'
'mul 1 1 1 1 -xint 1 -xwid 4.5 -ywid 4'
'd therr'
'draw title relative L2_norm (theta_bar)'
'gxprint ./fig/ERROR_thbar_'explab'.pdf'

**** --- fig 2 --
'set t 1 last'
'set z 'iz0' 'iz1
if (model='VVM')
'define thb=thbvvm'
'set z 'iz0
'define thb0=thbvvm0'
endif
if (model='VVMex')
'define thb=thbvvmex'
'set z 'iz0
'define thb0=thbvvmex0'
endif

pull c
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
'set time 'hr'Z'
'set cthick 10'
'set cmark 0'
'set cstyle 'snum
'set ccolor 'cnum
'd thb'
inum=inum+1
endwhile

'legend tl 'num' 5 10 'tlist' 'clist' 'slist
'draw title (a) 'model' / thbar [K]'

**  'set x 1'
**  'set y 1'
**  'set z 'iz0' 'iz1
**  'set t 1'
**  it=1
**  while(it<nt)
**  if (it=1); 'on'; else; 'off'; endif
**  'set cmark 0'
**  'set cthick 10'
**  'd thb(t='it')'
**  it=it+30*inthr
**  endwhile
**  'draw title thbar, interval 'inthr' hr'

'on'
'mul 2 1 2 1 -xint 1 -xwid 4.5 -ywid 4'
'set tlsupp month'
'set x 1'
'set y 1'
'set t 1 'nt
'set z 'iz0' 'iz1
'set clevs 0'
'set clab off'
'set cthick 10'
'set ccolor 1'
'set cstyle 1'
'd thbvvmex-thbvvmex0-0.5'

'off'
'set clevs 0'
'set clab off'
'set cthick 10'
'set ccolor 1'
'set cstyle 4'
'd thbvvm-thbvvm0-0.5'

'legend tr 2 5 10 VVMex VVM 1 1 1 4'
'draw title (b) PBL height (th_sfc+0.5K)'
'draw ylab [m]'

'gxprint ./fig/tg2_'model'_'explab'.pdf'
