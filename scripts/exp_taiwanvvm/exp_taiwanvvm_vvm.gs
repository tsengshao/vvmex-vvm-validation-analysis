'reinit'
'set background 1'
'c'

model='VVM'
exp='taiwanvvm'
dir='../../cpu/case_taiwanvvm_f1_aaron/gs_ctl_files/'

exp='taiwanvvmlarge'
dir='../../cpu/case_taiwanvvm_f1_Large_aaron/gs_ctl_files/'

figdir='./fig/'exp'/'
'! mkdir -p 'figdir'/'model


* initial profile
'open 'dir'/bar.ctl'
'set x 1'
'set y 1'
'set t 1'
'set vrange 310 400'
'd the'
'd thes'
'd const(lev,380);ug;vg'
'd 380+mag(ug,vg)'
'draw title 'model' / initial'
'gxprint 'figdir'/'model'_initial.pdf'
pull c

'reinit'
'set background 1'
'c'

'open 'dir'/dynamic.ctl'
'open 'dir'/surface.ctl'
'open 'dir'/topo.ctl'

'q file'
line=sublin(result,5)
nx=subwrd(line,3) 
ny=subwrd(line,6)
nz=subwrd(line,9)
nt=subwrd(line,12)


m=0
while(m<=24)
say m
'c'
'set grads off'
'set x 1 1024'
'set y 1 1024'
*'set x 1 2048'
*'set y 1 2048'
'set z 1'
'set t 1'
*X Limits = 2.58333 to 8.41667
*Y Limits = 0.75 to 7.75
'set parea 2.58333 8.41667 0.75 7.75'

'set mpdset hires'
'set map 1 1 8'
'set xlopts 1 5 0.2'
'set ylopts 1 5 0.2'

'set mproj off'
*'color 0 3000 100 -kind black->white'
'color 0 3000 100 -kind (255,255,255,0)-(0)->(250,250,250)->(100,100,100)'
'd height.3(z=1,t=1)*1000.'

'set gxout contour'
'set clevs 0.0001'
'set cthick 10'
'set ccolor 1'
'set clab off'
'd height.3(z=1,t=1)'

if (m=0)
*tt=(m-1)*144+2
*tt1=m*144+1
tt=2
tt1=(m+1)*144+1
'define k1=ave(sprec.2(z=1),t='tt',t='tt1')*86400'
else
tt=(m-1)*6+2
tt1=(m)*6+1
'define k1=ave(sprec.2(z=1),t='tt',t='tt1')*3600'
endif

'cwbraincol.gs'
'set gxout shaded'
'set xlint 1'
'set ylint 1'
'd k1'
'cbar.gs'
'draw map 1 1 8'
'set lev 500'
'set cthick 5'
'set ccolor 1'
'set gxout stream'
'set strmden -10'
*'d u.1;v.1'
'q time'
res=subwrd(result,3)
res1=substr(res,7,15)
*'draw title 'res1''
if (m=0)
'draw title 'model' / rain [mm/day]'
else
'draw title 'model' /rain [mm/hr] 'm-1'LT'
endif

mm=math_format( '%02.0f', m)
'gxprint 'figdir'/'model'/'model'_rain'mm'.png white x3000 y2318'

if(m=0)
* draw timeseries of land
'set t 1 last'
'set x 1'
'set y 1'
'define rland=3600*aave(maskout(sprec.2,height.3(t=1,z=1)-0.000005),x=1,x='nx',y=1,y='ny')'
pull c
'c'
'set tlsupp month'
'set vrange -0.1 2.5'
'd rland'
'draw title rain over land / 'model
*'gxprint rain_land.png'
'gxprint 'figdir'/'model'_rain_series.pdf'
endif

*pull v
m=m+1
endwhile


