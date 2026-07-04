function main(args)
* --- Read arguments for parallel chunks ---
tstart = subwrd(args,1)
tend   = subwrd(args,2)

if (tstart = '')
  say 'Error: Missing start and end time steps.'
  exit
endif

if (tend = '')
  tend = tstart
endif

model='VVM'
dir='../../cpu/case_rce_f1_aaron_rad/gs_ctl_files/'

outPath='./figs_cwv_'model'/'
say outPath
'! mkdir -p 'outPath

'reinit'
'set background 1'
'c'
'open 'dir'/thermodynamic.ctl'
'open 'dir'/surface.ctl'
'open 'dir'/bar.ctl'

* get data info
'q file'
line = sublin(result, 5)
nx = subwrd(line, 3)
ny = subwrd(line, 6)
nz = subwrd(line, 9)
nt = subwrd(line, 12)
*dt = 60mins
dt = 60

it = tstart
te = tend
while(it<=te)
say 't='it''
'c'
'set t 'it

'set lwid 77 10'
'set lwid 75 5'

'set parea 2.58333 8.41667 0.8 7.55'
'set xlopts 1 75 0.2'
'set ylopts 1 75 0.2'
'set grads off'
'set timelab off'
'set mpdraw off'
'set xlabs -576|-288|0|288|576'
'set ylabs -576|-288|0|288|576'


***** draw cwv *****
'color 10 60 2 -kind white->wheat->darkcyan->darkblue->(4,130,191) -gxout grfill'
lnum=(60-10)/2+2+15
'set rgb 'lnum' 0 250 250'

*calculate CWV
'set x 1'
'set y 1'
'set z 1 'nz
'define wg=rho.3(t=1)*dzt.3(t=1)'
'set x 1 'nx
'set y 1 'ny
'set z 1 'nz
'define dum=wg*qv.1'
'set z 1'
if(it=1)
'define cwv=sum(dum,z=1,z='nz')+lon*0.0000000001'
else
'define cwv=sum(dum,z=1,z='nz')'
endif
'd cwv'

'xcbar 8.7 9.0 0.8 7.55 -ft 75 -fs 5'

**  ***** draw rain *****
**  'set clab off'
**  *'set lwid 50 3'
**  'set lwid 50 7'
**  'set cthick 50'
**  'set gxout contour'
**  'set clevs 1'
**  'set ccolor 2'
**  'd sprec.2(z=1)*3600'

***** draw olr *****
*'color 100 220 10 -kind (255,255,255)-(0)->(255,255,255,0) -gxout shaded'
*'d olr.2(z=1)'

***** draw center point *****
*green
'set rgb 40 67 100 0'
*orange
'set rgb 41 230 140 0'
*purple
'set rgb 40 130 0 255'

***** draw text *****
'set string 1 bl 77 0'
'set strsiz 0.2'
'draw string 8.68 8.05 CWV'
'draw string 8.68 7.7 [mm]'

*'set string 1 br 75 0'
*'set strsiz 0.10'
*'draw string 8.27 8 transparent white is OLR (100 to 220 W/m2)'

*'set string 2 br 75 0'
*'set strsiz 0.10'
*'draw string 8.27 8.2 red line is cwv = 30 [mm]'

***** draw x/y label *****
'set string 1 c 75'
'set strsiz 0.17'
'draw string 5.5 0.2 [km]'

'set string 1 c 75 90'
'set strsiz 0.17'
'draw string 1.7 4.375 [km]'

***** draw  title (exp name and time) *****
day=(it-1)*dt/60/24
dy=math_format( '%.3f', day)
dy00=math_format( '%.0f', day)
if ( day = dy00 ); dy=dy00; endif

hour=(it-1)*dt/60
hr=math_format('%.1f', hour)
hr00=math_format( '%.0f', hour)
if ( hour = hr00 ); hr=hr00; endif

'set string 1 bl 77 0'
'set strsiz 0.25'
*'draw string 2.6875 8 'title
'draw string 2.6875 7.65 'model

'set string 1 br 77 0'
'set strsiz 0.25'
'draw string 8.3125 7.65 'dy'days'
*'draw string 8.3125 7.65 'hr'hours'

*if ( mode="SAVEFIG" )
if ( TRUE )
  itt=math_format( '%06.0f', it)
  'gxprint 'outPath'/whi_'exp'_'itt'.png x2400 y1800 white'
  it = it+1
endif

* if ( mode="PAUSE" )
*   te=tlast
*   pull step
*   if(step='q'|step='quit'|step='exit');exit;endif
*   if(step='');it=it+1;continue;else
*     rc=valnum(step)
*     if(rc=0);step;pull step;endif
*     if(rc=1&step>0);it=step;endif
*   endif
* endif

endwhile



