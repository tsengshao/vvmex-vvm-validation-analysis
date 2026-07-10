* grads -a 1.777778
'reinit'
'set background 0'
'c'
'sdfopen ./data/daily_rain_cf/taiwanvvm_1024x1024_VVMex_VVM_daily_rain_skip0_days1_halfshift_rollx0_rolly0_cf.nc'
'set xlopts 1 5 0.2'
'set ylopts 1 5 0.2'
i=1
varlist='rain_vvmex rain_vvm'
while(i<=2)
var=subwrd(varlist,i)
'mul 2 1 'i' 1 -xint 1 -xwid 4.5 -ywid 4'
'set xlint 1'
'set ylint 0.5'
'set mproj off'
'color 0 3000 100 -kind (255,255,255,0)-(0)->(250,250,250)->(100,100,100)'
'd height'
*'cbar.gs'
'cwbraincol.gs'
'set gxout shaded'
'set xlint 1'
'set ylint 1'
'd 'var
*'cbar.gs'
'set gxout contour'
'set clevs 0'
'set cthick 5'
'set ccolor 1'
'set clab off'
'd height'
i=i+1
endwhile
taiwanvvm.gs 
! vim taiwanvvm.gs 
taiwanvvm.gs 
ls data/
! ls data/
! ls data/daily_rain_cf/
! vim taiwanvvm.gs 
taiwanvvm.gs 
! vim taiwanvvm.gs 
taiwanvvm.gs 
! vim taiwanvvm.gs 
taiwanvvm.gs 
! vim taiwanvvm.gs 
taiwanvvm.gs 
! vim taiwanvvm.gs 
taiwanvvm.gs 
! vim taiwanvvm.gs 
taiwanvvm.gs 
! vim taiwanvvm.gs 
:wq
taiwanvvm.gs 
! vim taiwanvvm.gs 
taiwanvvm.gs 
q dim
q gsinfo
q gxinfo
xcbar 4.3 4.5 0.8 4 
xcbar 4.3 4.5 1 3.5 
c
taiwanvvm.gs 
xcbar 4.3 4.5 1 3.5 
xcbar 4.3 4.5 1 3.5.5 
c
taiwanvvm.gs 
xcbar 4.3 4.5 1 3.5.5 
xcbar 4.3 4.5 1 3 5.5 
xcbar 4.3 4.5 1 5.5 
c
taiwanvvm.gs 
q gxinfo
xcbar 4.3 4.5 1 4 
xcbar 4.2 4.4 1 4 
xcbar 4.1 4.3 1 4 
xcbar 4.0 4.1 1 4 
c
taiwanvvm.gs 
xcbar 4.0 4.1 1 4 
taiwanvvm.gs 
xcbar 4.0 4.15 1 4 
xcbar 4.4 4.55 1 4 
xcbar 4.5 4.65 1 4 
xcbar 4.6 4.75 1 4 
xcbar 4.7 4.85 1 4 
xcbar 4.7 4.8 1 4 
c
xcbar 4.7 4.8 1 4 
taiwanvvm.gs 
xcbar 4.7 4.83 1 4 
xcbar 4.0 4.15 1 4 
xcbar 4.7 4.83 1 4 
! vim taiwanvvm.gs 
taiwanvvm.gs 
! vim taiwanvvm.gs 
taiwanvvm.gs 
! vim taiwanvvm.gs 
taiwanvvm.gs 
! vim taiwanvvm.gs 
taiwanvvm.gs 
! vim taiwanvvm.gs 
taiwanvvm.gs 
c
set x 1 
set y 1 
d amax(height,x=1,x=2048,y=1,y=2048)
! vim taiwanvvm.gs 
d amax(height,x=1,x=2048,y=1,y=2048)
taiwanvvm.gs 
d amax(height,x=1,x=2048,y=1,y=2048)
taiwanvvm.gs 
! vim taiwanvvm.gs 
taiwanvvm.gs 
! vim taiwanvvm.gs 
taiwanvvm.gs 
! vim taiwanvvm.gs 
taiwanvvm.gs 
! vim taiwanvvm.gs 
taiwanvvm.gs 
! vim taiwanvvm.gs 
! vim taiwanvvm.gs 
q gxinfo
! vim taiwanvvm.gs 
taiwanvvm.gs 
q gxinfo
! vim taiwanvvm.gs 
taiwanvvm.gs 
! vim taiwanvvm.gs 
taiwanvvm.gs 
! vim taiwanvvm.gs 
taiwanvvm.gs 
! vim taiwanvvm.gs 
q gxinfo
! vim taiwanvvm.gs 
taiwanvvm.gs 
! vim taiwanvvm.gs 
taiwanvvm.gs 
! vim taiwanvvm.gs 
! vim taiwanvvm.gs 
! vim taiwanvvm.gs 
taiwanvvm.gs 
! vim taiwanvvm.gs 
taiwanvvm.gs 
! vim taiwanvvm.gs 
taiwanvvm.gs 
! vim taiwanvvm.gs 
taiwanvvm.gs 
! vim taiwanvvm.gs 
taiwanvvm.gs 
! vim taiwanvvm.gs 
taiwanvvm.gs 
! vim taiwanvvm.gs 
! vim taiwanvvm.gs 
taiwanvvm.gs 
! vim taiwanvvm.gs 
taiwanvvm.gs 
! vim taiwanvvm.gs 
taiwanvvm.gs 
! vim taiwanvvm.gs 
q gxinfo
! vim taiwanvvm.gs 
q gxinfo
taiwanvvm.gs 
q gxinfo
! vim taiwanvvm.gs 
q gxinfo
taiwanvvm.gs 
q gxinfo
taiwanvvm.gs 
! vim taiwanvvm.gs 
taiwanvvm.gs 
! vim taiwanvvm.gs 
taiwanvvm.gs 
! vim taiwanvvm.gs 
taiwanvvm.gs 
! vim taiwanvvm.gs 
! vim taiwanvvm.gs 
! vim taiwanvvm.gs 
taiwanvvm.gs 
! vim taiwanvvm.gs 
taiwanvvm.gs 
! vim taiwanvvm.gs 
taiwanvvm.gs 
! vim taiwanvvm.gs 
taiwanvvm.gs 
! vim taiwanvvm.gs 
taiwanvvm.gs 
! vim taiwanvvm.gs 
taiwanvvm.gs 
! vim taiwanvvm.gs 
:wq
! vim taiwanvvm.gs 
:wq
! vim taiwanvvm.gs 
:wq
taiwanvvm.gs 
! vim taiwanvvm.gs 
taiwanvvm.gs 
! vim taiwanvvm.gs 
q gxinfo
! vim taiwanvvm.gs 
taiwanvvm.gs 
quit # (End of session: 10Jul2026, 08:30:09)
