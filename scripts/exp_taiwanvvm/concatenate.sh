#!/bin/bash

vvmPath="/data3/C.shaoyu/VVM_Sharon/cpu/exp"

outVvmPath="/work1/umbrella0c/VVM/DATA"
outVvmPath="/data3/C.shaoyu/VVM_Sharon/cpu/"

typeList="C.Surface L.Dynamic L.Radiation L.Thermodynamic"
expList="case_taiwanvvm_f1_Large_aaron"


make_ctl_script="/data3/C.shaoyu/VVM/DATA/mountain_aaron_new/make_ctl_bash.sh"

for exp in ${expList};do
  echo "----- ${exp} -----"

  dir="${vvmPath}/${exp}/"
  if [ ! -d ${dir} ];then
    echo "can't found the case '${exp}' ... skip"
    continue
  fi
  out="${outVvmPath}/${exp}/"
  rm -rf ${out}

  echo "create ... ${out}"
  mkdir -p ${out}
  ln -sf ${dir}/TOPO.nc       ${out}/
  ln -sf ${dir}/fort.98       ${out}/
  ln -sf ${dir}/vvm.setup     ${out}/
  ln -sf ${dir}/INPUT         ${out}/
  ln -sf ${dir}/DOMAIN        ${out}/
  ln -sf ${dir}/definesld.com ${out}/
  ln -sf ${dir}/bar.dat       ${out}/
  cp ${make_ctl_script} ${out}/
  mkdir ${out}/restart_log

  n=$(ls -d ${vvmPath}/${exp}_*|wc -l)
  if [ ${n} -le 0 ]; then
    ln -sf ${dir}/archive     ${out}/
    echo "no restart folder ..."
    continue
  fi

  echo "There are ${n} folder to be merged ..."
  mkdir ${out}/archive
  ln -sf ${dir}/archive/*.nc ${out}/archive/
  for i in $(seq 1 ${n}) ;do
    echo "process the restart_${i} ..."
    dir="${vvmPath}/${exp}_${i}/"
    if [ ! -d ${dir} ];then
      echo "can't found the restart folder: ${dir} ..."
      echo "please check the rule of the restart folder ... skip"
      break
    fi

    if [ ${i} -eq 1 ]; then
      pre_exp=${exp}
    else
      i0=$(echo ${i}-1|bc)
      pre_exp=${exp}_${i0}
    fi

    idx0="notfound"
    if [ -f ${dir}/restart.log ];then
      cp -r "${dir}/restart.log" ${out}/restart_log/restart_${i}.log
      idx0=$(head -n 1 ${dir}/restart.log|rev|cut -d" " -f1|rev)
    else
      idx0=$(grep "${pre_exp}.L.Thermodynamic" \
            ${vvmPath}/${exp}_${i}/CODE/ini_3d_module.F|\
            rev|cut -d"-" -f1|rev|cut -c1-6)
      echo "restart timestep ... ${idx0} 
            from ${vvmPath}/${exp}_${i}/CODE/ini_3d_module.F" > ${out}/restart_log/restart_${i}.log
    fi

    if [ "${idx0}" == "notfound" ]; then
      echo "can't found the restart timestep ... skip"
      break
    fi
   
    if [ ${i} -eq 1 ]; then
      lastnum=${idx0}
    else
      dum=$(ls ${vvmPath}/${pre_exp}/archive/${pre_exp}.C.Surface*.nc|wc -l)
      lastnum=$(echo "${lastnum}-(${dum}-1-${idx0})"|bc)
    fi
 
    nfile=$(ls ${dir}/archive/${exp}_${i}.C.Surface*.nc|wc -l)
    nfile=$(echo ${nfile}-1|bc)
    echo "restart init_timestep is ${idx0} and the total number is ${nfile} ... ${lastnum}"
    for inc in $(seq 1 ${nfile});do
      inc=$(printf "%06d" ${inc})
      idx=$(echo ${lastnum}+${inc}|bc)
      idx=$(printf "%06d" ${idx})
      #echo "${inc}-->${idx}"
      for vtype in ${typeList};do
        #echo ${dir}/archive/${exp}_${i}.${vtype}-${inc}.nc
        ln -sf ${dir}/archive/${exp}_${i}.${vtype}-${inc}.nc \
               ${out}/archive/${exp}.${vtype}-${idx}.nc
      done
    done # inc
    lastnum=${lastnum}+${nfile}

  done # restart folder (i)
  lastnum=$(echo ${lastnum}|bc)
  echo "total timestep ... ${lastnum}"

  echo "start to create the ctl files ... "
  ${out}/make_ctl_bash.sh


done #exp
