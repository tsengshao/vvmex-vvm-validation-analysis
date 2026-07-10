* grads -a 1.777778
'reinit'
'set background 1'
'c'

domain=1024
*domain=2048

if (domain=1024)
'sdfopen ./data/daily_rain_cf/taiwanvvm_1024x1024_VVMex_VVM_daily_rain_skip0_days1_halfshift_rollx0_rolly0_cf.nc'
else
'sdfopen ./data/daily_rain_cf/taiwanvvmlarge_2048x2048_VVMex_VVM_daily_rain_skip0_days1_halfshift_rollx512_rolly512_cf.nc'
endif

'set xlopts 1 5 0.2'
'set ylopts 1 5 0.2'
i=1
varlist='rain_vvmex rain_vvm'
titlelist='VVMex VVM'
while(i<=2)
var=subwrd(varlist,i)
title=subwrd(titlelist,i)
'mul 2 1 'i' 1 -yini 1 -xini 1 -xint 0.6 -xwid 4.5 -ywid 4.5'

'set xlint 2'
'set ylint 2'
'set mproj off'
'set timelab off'
'set grads off'

'on'
'color 0 3.5 0.5 -kind (255,255,255,0)-(0)->(250,250,250)->(100,100,100)'
'd height*1e-3'

'q gxinfo'
line=sublin(result, 3)
line2=sublin(result, 4)
x1=subwrd(line,4)
x2=subwrd(line,6)
y1=subwrd(line2,4)
y2=subwrd(line2,6)

if(i=2)
*X Limits = 0.752 to 5.252
*Y Limits = 0.8 to 5.3
xlen=0.15
ylen=2.8
xoffset=1.2
yoffset=0.1
xint=0.65
'xcbar 'x2-xoffset-xlen' 'x2-xoffset' 'y1+yoffset' 'y1+yoffset+ylen
endif

'off'
'cwbraincol.gs'
'set gxout shaded'
'set xlint 1'
'set ylint 1'
'd 'var

if(i=2)
'xcbar 'x2-xoffset-xlen+xint' 'x2-xoffset+xint' 'y1+yoffset' 'y1+yoffset+ylen
endif

'set gxout contour'
'set clevs 0'
'set cthick 5'
'set ccolor 1'
'set clab off'
'd height'
'draw title 'title

x=(x1+x2)/2
y=y1-0.5
'set strsiz 0.17'
'set string 1 tc 5 0'
'draw string 'x' 'y' Longitude [`ao`n]'

if(i=1)
x=x1-0.65
y=(y1+y2)/2
'set string 1 bc 5 90'
'draw string 'x' 'y' Latitude [`ao`n]'
endif

if(i=2)
'set strsiz 0.12'
'set string 1 bl 2 0'
'draw string 'x2-xoffset-xlen' 'y1+yoffset+ylen+0.12' [km]'
'draw string 'x2-xoffset-xlen+xint-0.1' 'y1+yoffset+ylen+0.12' [mmd`a-1`n]'
endif


'gxprint ./fig/combine_taiwanvvm_'domain'.pdf'
*'gxprint ./fig/combine_taiwanvvm_'domain'.png white x3300 y1856'

i=i+1
endwhile

