'reinit'
'set background 1'
'c'

'open ../../gpu/testing_output_2dbubble/vvm.ctl'
'open ../../cpu/2dbubble_0703/gs_ctl_files/thermodynamic.ctl'

model='VVMex'
*model='VVM'
'! mkdir -p ./fig_'model
'! mkdir -p ./pdf_'model

if(model='VVMex')
  var='th'
else
  var='th.2'
endif
say model' 'var

nz=33

'c'
'set z 1 'nz
'set x 1 32'
'set y 16'
*'set lwid 75 5'
'set lwid 75 2'

t=1
while(t<=61)
'c'

ti=(t-1)
'set t 't

'set parea 1.5 10.5 1 7'
'set grads off'
'set timelab off'

'set xlopts 1 75 0.2'
'set ylopts 1 75 0.2'
'set xlabs -8|-6|-4|-2|0|2|4|6|8'

'set gxout contour'
'color 0.1 5 0.1 -kind grainbow -gxout contour'
'set cthick 10'
'd 'var'-ave('var'(t=1),x=1,x=1)'

'set strsiz 0.25'
'set string 1 tc 75 0'
'draw string 6 0.5  [km]'

'set string 1 bl 75 0'
'set strsiz 0.25'
'draw string 1.5 7.3 'model' / 'ti' mins'

itt=math_format( '%06.0f', t)
*'gxprint ./fig_'model'/bubble2d_'model'_'itt'.png white x3000 y2400'
'gxprint ./pdf_'model'/bubble2d_'model'_'itt'.pdf'

*pull c
t=t+1
endwhile

