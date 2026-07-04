'reinit'
'set background 1'
'c'

'open ../../gpu/mountain_noturb/vvm.ctl'
'open ../../cpu/mountain_aaron_new_noturb/gs_ctl_files/dynamic.ctl'
'open ../../cpu/mountain_aaron_new_noturb/gs_ctl_files/bar.ctl'
nz=74

'set x 1'
'set y 1'
'set t 1'
'set z 1 'nz
'wei=dzt.3*rho.3'
*'wei=1'

'set lwid 75 8'
'set lwid 75 2'

'set x 1'
'set y 1'
'set z 1'
'set t 1 last'
'define a=sqrt(mean(amean(pow(w.1*wei-w.2*wei,2),x=1,x=512,y=1,y=1),z=1,z='nz'))'
'define b=sqrt(mean(amean(pow(w.2*wei,2),x=1,x=512,y=1,y=1),z=1,z='nz'))'
'define werr=a/maskout(b,b>0.000001)'

'd werr'
'draw title relative L`b2`n norm'
*'gxprint error_mountain.png white x3000 y2400'
'gxprint error_mountain.pdf'



pull c
'c'
'set z 1 51'
'set x 206 306'
'set y 1'

*topo
'define mask=maskout(1, u.1(t=5)>0.)'
'define topomask=maskout(1, u.1(t=5)<=0.)'

* 'set cint 0.25'
* 'd w.2'
*'define err=(w.1 - w.2)/maskout(w.2,abs(w.2)>0.000001)*100.'
** 'define err=w.1-w.2'
** 'set gxout shaded'
** 'set clevs -0.05 0.05'
** 'set ccols 1 -1 2'
** 'd err'

t=11
ti=(t-1)*2
'set t 't

'set parea 1.5 10.5 1 7'
'set grads off'
'set timelab off'

'set xlopts 1 75 0.2'
'set ylopts 1 75 0.2'
'set xlabs -10|-5|0|5|10'
'set ylabs 0|2|4|6|8|10'

'set gxout contour'

'set ccolor 1'
'set cthick 75'
'set cint 0.25'
*'set black -0.001 0.001'
'set cstyle 2'
'set cmax -0.25'
'd maskout(w.2,mask)'

'set ccolor 1'
'set cthick 75'
'set cint 0.25'
*'set black -0.001 0.001'
'set cstyle 1'
'set cmin 0.25'
'd maskout(w.2,mask)'

'set gxout grfill'
'set ccolor 1'
'd topomask'

'set strsiz 0.25'
'set string 1 tc 75 0'
'draw string 6 0.5  [km]'
'set string 1 bc 75 90'
'draw string 0.7 4  [km]'


'set string 1 bl 75 0'
'set strsiz 0.25'
*X Limits = 1 to 10
*Y Limits = 1 to 7
'draw string 1.5 7.3 VVMex / 'ti' mins'

'd werr'
say result
errnum=subwrd(result,4)
'set string 1 br 75 0'
'draw string 10.5 7.3 L`b2`n='errnum

*'gxprint mountain_VVMex.png white x3000 y2400'
'gxprint mountain_VVMex.pdf'

pull c
'c'
'set parea 1.5 10.5 1 7'
'set grads off'
'set timelab off'

'set xlopts 1 75 0.2'
'set ylopts 1 75 0.2'
'set xlabs -10|-5|0|5|10'
'set ylabs 0|2|4|6|8|10'

'set gxout contour'

'set ccolor 1'
'set cthick 75'
'set cint 0.25'
*'set black -0.001 0.001'
'set cstyle 2'
'set cmax -0.25'
'd maskout(w.2,mask)'

'set ccolor 1'
'set cthick 75'
'set cint 0.25'
*'set black -0.001 0.001'
'set cstyle 1'
'set cmin 0.25'
'd maskout(w.2,mask)'


'set gxout grfill'
'set ccolor 1'
'd topomask'
'set string 1 tc 75 0'
'draw string 6 0.5  [km]'
'set string 1 bc 75 90'
'draw string 0.7 4  [km]'

'set string 1 bl 75 0'
'set strsiz 0.25'
*X Limits = 1 to 10
*Y Limits = 1 to 7
'draw string 1.5 7.3 VVM / 'ti' mins'

*'gxprint mountain_cpu.png white x3000 y2400'
'gxprint mountain_VVM.pdf'
