function cwbraincol(divisor)
if(divisor="");divisor=1;endif
d=subwrd(divisor,1)
*cbar of CWB precipitation
'set rgb 101 201 192 195 0'
'set rgb 102 159 254 250 '
'set rgb 103 000 206 255 '
'set rgb 104 001 152 255 '
'set rgb 105 000 104 250 '
'set rgb 106 048 153 001 '
'set rgb 107 050 255 000 '
'set rgb 108 254 255 001 '
'set rgb 109 255 203 001 '
'set rgb 110 255 148 007 '
'set rgb 111 250 003 000 '
'set rgb 112 200 001 004 '
'set rgb 113 158 000 000 '
'set rgb 114 152 000 154 '
'set rgb 115 206 000 212 '
'set rgb 116 255 000 243 '
'set rgb 117 252 206 255 '
*interval: 1 2 6 10 15 20 30 40 50 70 90 110 130 150 200 300
'set clevs  '1/d' '2/d' '6/d' '10/d' '15/d' '20/d' '30/d' '40/d' '50/d' '70/d' '90/d' '110/d' '130/d' '150/d' '200/d' '300/d
say 'set clevs  '1/d' '2/d' '6/d' '10/d' '15/d' '20/d' '30/d' '40/d' '50/d' '70/d' '90/d' '110/d' '130/d' '150/d' '200/d' '300/d''
'set ccols  101 102 103 104 105 106 107 108 109 110 111 112 113 114 115 116 117'
say "set ccols  101 102 103 104 105 106 107 108 109 110 111 112 113 114 115 116 117"
