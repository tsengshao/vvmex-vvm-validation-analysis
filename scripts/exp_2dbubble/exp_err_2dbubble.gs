
*16:6 grads -a 2.6666667
'reinit'
'set background 1'
'c'

*../../gpu/testing_output_2dbubble/
'open ../../gpu/testing_output_2dbubble/vvm.ctl'
'open ../../cpu/2dbubble_0703/gs_ctl_files/dynamic.ctl'
'open ../../cpu/2dbubble_0703/gs_ctl_files/thermodynamic.ctl'
nz=33

'set x 1'
'set y 1'
'set t 1'
'set z 1 'nz
'wei=1'

'set x 1'
'set y 1'
'set z 1'
'set t 1 last' 
varvvmex='w.1*wei'
varvvm='w.2*wei'
'define a=sqrt(mean(amean(pow('varvvmex'-'varvvm',2),x=1,x=32,y=1,y=1),z=1,z='nz'))'
'define b=sqrt(mean(amean(pow('varvvm',2),x=1,x=32,y=1,y=1),z=1,z='nz'))'
'define werr=a/maskout(b,b>0.000001)'

varvvmex='eta.1*wei'
varvvm='eta.2*wei'
'define a=sqrt(mean(amean(pow('varvvmex'-'varvvm',2),x=1,x=32,y=1,y=1),z=1,z='nz'))'
'define b=sqrt(mean(amean(pow('varvvm',2),x=1,x=32,y=1,y=1),z=1,z='nz'))'
'define etaerr=a/maskout(b,b>0.000001)'

varvvmex='th.1*wei'
varvvm='th.3*wei'
'define a=sqrt(mean(amean(pow('varvvmex'-'varvvm',2),x=1,x=32,y=1,y=1),z=1,z='nz'))'
'define b=sqrt(mean(amean(pow('varvvm',2),x=1,x=32,y=1,y=1),z=1,z='nz'))'
'define therr=a/maskout(b,b>0.000001)'

num=3

'set tlsupp month'
'set grads off'
'set timelab off'

'set cthick 10'

'set ccolor 1'
'd therr'

'set ccolor 2'
'd etaerr'

'set ccolor 3'
'd werr'

tlist='th eta w'
'legend br 'num' 5 10 'tlist' 1 2 3 '

'draw title 2d_bubble / Relative L`b2`n norm'

'gxprint error_bubble2d.pdf'

