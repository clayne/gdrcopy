%{!?_release: %define _release 1}
%{!?CUDA: %define CUDA /usr/local/cuda}
%{!?GDR_VERSION: %define GDR_VERSION 2.0}
%{!?KVERSION: %define KVERSION %(uname -r)}
%{!?MODULE_LOCATION: %define MODULE_LOCATION /kernel/drivers/misc/}
%{!?NVIDIA_DRIVER_VERSION: %define NVIDIA_DRIVER_VERSION UNKNOWN}
%{!?NVIDIA_SRC_DIR: %define NVIDIA_SRC_DIR UNDEFINED}
%{!?BUILD_KMOD: %define BUILD_KMOD 0}
%global debug_package %{nil}
%global krelver %(echo -n %{KVERSION} | sed -e 's/-/_/g')
%define MODPROBE %(if ( /sbin/modprobe -c | grep -q '^allow_unsupported_modules  *0'); then echo -n "/sbin/modprobe --allow-unsupported-modules"; else echo -n "/sbin/modprobe"; fi )
%define usr_src_dir /usr/src

# For DKMS, dynamic
%define dkms_kernel_version $(uname -r)
# For kmod, static
%define kmod_kernel_version %{KVERSION}

%define kernel_version %{dkms_kernel_version}
%define old_driver_install_dir /lib/modules/%{kernel_version}/%{MODULE_LOCATION}

# This is to set the dkms package name. For backward compatibility with the previous versions, we need to keep using "kmod".
%global dkms kmod

%if %{BUILD_KMOD} > 0
%global kmod_fullname kmod-%{kmod_kernel_version}-%{NVIDIA_DRIVER_VERSION}
%endif

%define gdrcopy_service_install_script                                  \
%if 0%{!?suse_version:1}                                                \
# RHEL                                                                  \
%if 0%{?rhel} >= 9                                                      \
if [ -e /usr/bin/systemctl ]; then                                      \
    /usr/bin/systemctl enable gdrcopy||:                                \
    /usr/bin/systemctl start gdrcopy||:                                 \
fi                                                                      \
%else                                                                   \
# RHEL 8 or earlier                                                     \
if ! ( /sbin/chkconfig --del gdrcopy > /dev/null 2>&1 ); then           \
   true                                                                 \
fi                                                                      \
/sbin/chkconfig --add gdrcopy                                           \
service gdrcopy start                                                   \
%endif                                                                  \
# No service for SUSE                                                   \
%endif

%define gdrcopy_service_uninstall_script                                \
%if 0%{!?suse_version:1}                                                \
# RHEL                                                                  \
%if 0%{?rhel} >= 9                                                      \
if [ -e /usr/bin/systemctl ]; then                                      \
    /usr/bin/systemctl stop gdrcopy||:                                  \
    /usr/bin/systemctl disable gdrcopy||:                               \
fi                                                                      \
%else                                                                   \
# RHEL 8 or earlier                                                     \
service gdrcopy stop||:                                                 \
%{MODPROBE} -rq gdrdrv||:                                               \
if ! ( /sbin/chkconfig --del gdrcopy > /dev/null 2>&1 ); then           \
   true                                                                 \
fi                                                                      \
%endif                                                                  \
%else                                                                   \
# No service for SUSE but we still need to unload the driver            \
%{MODPROBE} -rq gdrdrv||:                                               \
%endif


%define gdrdrv_install_script                                           \
/sbin/depmod -a %{kernel_version} &> /dev/null ||:                      \
%{MODPROBE} -rq gdrdrv||:                                               \
%{MODPROBE} gdrdrv||:                                                   \
%{gdrcopy_service_install_script}


%global dkms_install_script                                             \
echo "Start gdrcopy-kmod installation."                                 \
dkms add -m gdrdrv -v %{version} -q --rpm_safe_upgrade || :             \
                                                                        \
# Rebuild and make available for all installed kernel                   \
echo "Building and installing to all available kernels."                \
echo "This process may take a few minutes ..."                          \
for kver in $(ls -1d /lib/modules/* | cut -d'/' -f4)                    \
do                                                                      \
    dkms build -m gdrdrv -v %{version} -k ${kver} -q || :               \
    dkms install -m gdrdrv -v %{version} -k ${kver} -q --force || :     \
done                                                                    \
                                                                        \
%define kernel_version %{dkms_kernel_version}                           \
%{gdrdrv_install_script}


%global daemon_reload_script                                            \
if [ -e /usr/bin/systemctl ]; then                                      \
    /usr/bin/systemctl daemon-reload                                    \
fi

%global __requires_exclude ^libcuda\\.so.*$


Name:           gdrcopy
Version:        %{GDR_VERSION}
Release:        %{_release}%{?dist}
Summary:        GDRcopy library and companion kernel-mode driver    
Group:          System Environment/Libraries
License:        MIT
URL:            https://github.com/NVIDIA/gdrcopy
Source0:        %{name}-%{version}.tar.gz
BuildRequires:  gcc kernel-headers

%package devel
Summary: The development files
Group: System Environment/Libraries
Requires: %{name} = %{version}-%{_release}
BuildArch: noarch

%package %{dkms}
Summary: The kernel-mode driver
Group: System Environment/Libraries
Requires: dkms >= 1.00
Requires: bash
Release: %{_release}%{?dist}dkms
BuildArch: noarch
Provides: %{name}-kmod = %{version}-%{_release}
%if 0%{?rhel} >= 8
# Recommends tag is a weak dependency, whose support started in RHEL8.
# See https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/8/html/packaging_and_distributing_software/new-features-in-rhel-8_packaging-and-distributing-software#support-for-weak-dependencies_new-features-in-rhel-8.
Recommends: kmod-nvidia-latest-dkms
%endif

%if %{BUILD_KMOD} > 0
# This is the real kmod package, which contains prebuilt gdrdrv.ko.
%package %{kmod_fullname}
Summary: The kernel-mode driver
Group: System Environment/Libraries
Release: %{_release}%{?dist}
Provides: %{name}-kmod = %{version}-%{_release}
%endif

%description
GDRCopy, a low-latency GPU memory copy library and a kernel-mode driver, built on top of the 
NVIDIA GPUDirect RDMA technology.

%description devel
GDRCopy, a low-latency GPU memory copy library and a kernel-mode driver, built on top of the 
NVIDIA GPUDirect RDMA technology.

%description %{dkms}
Kernel-mode driver for GDRCopy with DKMS support.

%if %{BUILD_KMOD} > 0
%description %{kmod_fullname}
Kernel-mode driver for GDRCopy built for GPU driver %{NVIDIA_DRIVER_VERSION} and Linux kernel %{KVERSION}.
%endif

%prep
%setup


%build
echo "building"
make -j8 CUDA=%{CUDA} config lib exes
%if %{BUILD_KMOD} > 0
make -j8 NVIDIA_SRC_DIR=%{NVIDIA_SRC_DIR} driver
%endif

%install
# Install gdrcopy library and tests
make install DESTDIR=$RPM_BUILD_ROOT prefix=%{_prefix} libdir=%{_libdir}

%if %{BUILD_KMOD} > 0
# Install gdrdrv driver
make drv_install DESTDIR=$RPM_BUILD_ROOT NVIDIA_SRC_DIR=%{NVIDIA_SRC_DIR}
%endif

# Install gdrdrv src
mkdir -p $RPM_BUILD_ROOT%{usr_src_dir}
mkdir -p $RPM_BUILD_ROOT%{usr_src_dir}/gdrdrv-%{version}
cp -a $RPM_BUILD_DIR/%{name}-%{version}/src/gdrdrv/gdrdrv.c $RPM_BUILD_ROOT%{usr_src_dir}/gdrdrv-%{version}/
cp -a $RPM_BUILD_DIR/%{name}-%{version}/src/gdrdrv/gdrdrv.h $RPM_BUILD_ROOT%{usr_src_dir}/gdrdrv-%{version}/
cp -a $RPM_BUILD_DIR/%{name}-%{version}/src/gdrdrv/Makefile $RPM_BUILD_ROOT%{usr_src_dir}/gdrdrv-%{version}/
cp -a $RPM_BUILD_DIR/%{name}-%{version}/src/gdrdrv/nv-p2p-dummy.c $RPM_BUILD_ROOT%{usr_src_dir}/gdrdrv-%{version}/
cp -a $RPM_BUILD_DIR/%{name}-%{version}/dkms.conf $RPM_BUILD_ROOT%{usr_src_dir}/gdrdrv-%{version}
cp -a -r $RPM_BUILD_DIR/%{name}-%{version}/scripts $RPM_BUILD_ROOT%{usr_src_dir}/gdrdrv-%{version}/

%if 0%{!?suse_version:1}
# RHEL

%if 0%{?rhel} >= 9
# Install systemd service
install -d $RPM_BUILD_ROOT/usr/libexec/gdrcopy
install -m 0755 $RPM_BUILD_DIR/%{name}-%{version}/init.d/gdrcopy $RPM_BUILD_ROOT/usr/libexec/gdrcopy
install -d $RPM_BUILD_ROOT/usr/lib/systemd/system
install -m 0644 $RPM_BUILD_DIR/%{name}-%{version}/gdrcopy.service $RPM_BUILD_ROOT/usr/lib/systemd/system
%else
# RHEL8 or earlier
# Install gdrdrv service script
install -d $RPM_BUILD_ROOT/etc/init.d
install -m 0755 $RPM_BUILD_DIR/%{name}-%{version}/init.d/gdrcopy $RPM_BUILD_ROOT/etc/init.d
%endif

%else # SUSE
mkdir -p $RPM_BUILD_ROOT/etc/modprobe.d
cat <<"EOF" > $RPM_BUILD_ROOT/etc/modprobe.d/50-gdrdrv.conf
#options gdrdrv dbg_enabled=1
#options info_enabled=1
install gdrdrv PATH=$PATH:/bin:/usr/bin; /sbin/modprobe --ignore-install gdrdrv $CMDLINE_OPTS && rm -f /dev/gdrdrv && mknod -m 660 /dev/gdrdrv c $(gawk '/gdrdrv/{printf"%%s",$1}' /proc/devices) 0 && chgrp video /dev/gdrdrv
remove gdrdrv PATH=$PATH:/bin:/usr/bin; /sbin/modprobe --remove --ignore-remove gdrdrv && rm -f /dev/gdrdrv
EOF
chmod 0644 $RPM_BUILD_ROOT/etc/modprobe.d/50-gdrdrv.conf
%endif

%post %{dkms}
if [ "$1" == "2" ] && [ -e "%{old_driver_install_dir}/gdrdrv.ko" ]; then
    echo "Old package is detected. Defer installation until after the old package is removed."

    # Prevent the uninstall scriptlet of the old package complaining about change in gdrcopy service
    %{daemon_reload_script}

    exit 0;
fi

# Prevent race with kmod-nvidia-latest-dkms triggerin
if [ ! -e "%{_localstatedir}/lib/rpm-state/gdrcopy-dkms/installed" ]; then
    %{dkms_install_script}
    mkdir -p %{_localstatedir}/lib/rpm-state/gdrcopy-dkms
    touch %{_localstatedir}/lib/rpm-state/gdrcopy-dkms/installed
fi


%if %{BUILD_KMOD} > 0
%post %{kmod_fullname}
%define kernel_version %{kmod_kernel_version}
%{gdrdrv_install_script}
%endif


%preun %{dkms}
%{gdrcopy_service_uninstall_script}

# Remove all versions from DKMS registry
echo "Uninstalling and removing the driver."
echo "This process may take a few minutes ..."
dkms uninstall -m gdrdrv -v %{version} -q --all || :
dkms remove -m gdrdrv -v %{version} -q --all --rpm_safe_upgrade || :

# Clean up the weak-updates symlinks
find /lib/modules/*/weak-updates -name "gdrdrv.ko.*" -delete &> /dev/null || :
find /lib/modules/*/weak-updates -name "gdrdrv.ko" -delete &> /dev/null || :


%if %{BUILD_KMOD} > 0
%preun %{kmod_fullname}
%{gdrcopy_service_uninstall_script}
%endif

%postun %{dkms}
%{daemon_reload_script}

%if %{BUILD_KMOD} > 0
%postun %{kmod_fullname}
%{daemon_reload_script}
%endif


%triggerpostun %{dkms} -- gdrcopy-kmod <= 2.1-1
%{dkms_install_script}


%triggerin %{dkms} -- kmod-nvidia-latest-dkms
if [ "$1" == "2" ] && [ -e "%{old_driver_install_dir}/gdrdrv.ko" ]; then
    echo "kmod-nvidia-latest-dkms is detected but defer installation because of the old gdrcopy-kmod package."
    exit 0;
fi

# Prevent race with post
if [ ! -e "%{_localstatedir}/lib/rpm-state/gdrcopy-dkms/installed" ]; then
    %{dkms_install_script}
    mkdir -p %{_localstatedir}/lib/rpm-state/gdrcopy-dkms
    touch %{_localstatedir}/lib/rpm-state/gdrcopy-dkms/installed
fi


%triggerun %{dkms} -- kmod-nvidia-latest-dkms
# This dkms package has only weak dependency with kmod-nvidia-latest-dkms, which is not enforced by RPM.
# Uninstalling kmod-nvidia-latest-dkms would not result in uninstalling this package.
# However, gdrdrv may prevent the removal of nvidia.ko.
# Hence, we rmmod gdrdrv before starting kmod-nvidia-latest-dkms uninstallation.
service gdrcopy stop||:
%{MODPROBE} -rq gdrdrv||:
service gdrcopy start > /dev/null 2>&1 ||:


%posttrans %{dkms}
# Cleaning up
if [ -e "%{_localstatedir}/lib/rpm-state/gdrcopy-dkms/installed" ]; then
    rm -f %{_localstatedir}/lib/rpm-state/gdrcopy-dkms/installed
fi


%clean
rm -rf $RPM_BUILD_DIR/%{name}-%{version}
[ "x$RPM_BUILD_ROOT" != "x" ] && rm -rf $RPM_BUILD_ROOT


%files
%{_prefix}/bin/apiperf
%{_prefix}/bin/copybw
%{_prefix}/bin/copylat
%{_prefix}/bin/sanity
%{_prefix}/bin/gdrcopy_apiperf
%{_prefix}/bin/gdrcopy_copybw
%{_prefix}/bin/gdrcopy_copylat
%{_prefix}/bin/gdrcopy_sanity
%{_prefix}/bin/gdrcopy_pplat
%{_libdir}/libgdrapi.so.?.?
%{_libdir}/libgdrapi.so.?
%{_libdir}/libgdrapi.so


%files devel
%{_prefix}/include/gdrapi.h
%{_prefix}/include/gdrconfig.h
%doc README.md


%files %{dkms}
%defattr(-,root,root,-)
%if 0%{!?suse_version:1}
%if 0%{?rhel} >= 9
/usr/libexec/gdrcopy/gdrcopy
/usr/lib/systemd/system/gdrcopy.service
%else
/etc/init.d/gdrcopy
%endif
%else
/etc/modprobe.d/50-gdrdrv.conf
%endif
%{usr_src_dir}/gdrdrv-%{version}/gdrdrv.c
%{usr_src_dir}/gdrdrv-%{version}/gdrdrv.h
%{usr_src_dir}/gdrdrv-%{version}/Makefile
%{usr_src_dir}/gdrdrv-%{version}/nv-p2p-dummy.c
%{usr_src_dir}/gdrdrv-%{version}/dkms.conf
%{usr_src_dir}/gdrdrv-%{version}/scripts/*


%if %{BUILD_KMOD} > 0
%files %{kmod_fullname}
%defattr(-,root,root,-)
%if 0%{!?suse_version:1}
%if 0%{?rhel} >= 9
/usr/libexec/gdrcopy/gdrcopy
/usr/lib/systemd/system/gdrcopy.service
%else
/etc/init.d/gdrcopy
%endif
%else
/etc/modprobe.d/50-gdrdrv.conf
%endif
%{old_driver_install_dir}/gdrdrv.ko
%endif


%changelog
* Fri Mar 21 2025 GPUDirect Team <gpudirect@nvidia.com> %{GDR_VERSION}-%{_release}
- See CHANGELOG.md.
* Fri Mar 21 2025 GPUDirect Team <gpudirect@nvidia.com> 2.5-%{_release}
- Introduce gdr_pin_buffer_v2 API, GDR_PIN_FLAG_FORCE_PCIE pin flag and the GDR_ATTR_SUPPORT_PIN_FLAG_FORCE_PCIE attribute. Extend gdrcopy_sanity coverage to those new APIs.
- Waive some unit tests in gdrcopy_sanity if the GPU compute mode is not set as default.
- Introduce gdr_get_attribute API and GDR_ATTR_USE_PERSISTENT_MAPPING.
- Add persistent mapping coverage to gdrcopy_sanity.
- Support setting GPU ID in gdrcopy_sanity.
- Fix nvidia_p2p_get_pages_persistent leakage in gdrdrv.
- Introduce leakage_pin_pages_fork_cumemalloc unit test.
- Add support for mix mappings.
- Introduce /proc/driver/gdrdrv/params and /proc/driver/gdrdrv/nv_get_pages_refcount.
- Fix silent failure in gdrcopy_copybw and gdrcopy_apiperf.
- Add -l to shmoo sizes in gdrcopy_copybw.
- Set the default NVCC_FLAGS to generate PTX and SASS for all supported architectures.
- Improve the error reporting in gdrcopy_pplat due to PTX loading errors.
- Add cold cache testing to gdrcopy_copylat.
- Fix errors in gdr_map due to PAT.
- Improve the gdrcopy_pplat algorithm and add more test cases.
- Improve vm_flags_set detection mechanism.
- Change the default to set use_persistent_mapping=1.
* Mon Dec 16 2024 Pak Markthub <pmarkthub@nvidia.com> 2.4.4-%{_release}
- Fix the use-after-free bug of mr objects in gdrdv_vma_close.
- Fix the resource leakage bug in gdrdrv_release.
* Mon Dec 02 2024 Pak Markthub <pmarkthub@nvidia.com> 2.4.3-%{_release}
- Fix NVIDIA_IS_OPENSOURCE detection when compile with NVIDIA driver version 545 or newer.
* Thu Oct 31 2024 Pak Markthub <pmarkthub@nvidia.com> 2.4.2-%{_release}
- Fix the size alignment bug in gdrdrv.
- Fix memory leak in gdr_pin_buffer.
- Add support for another flavor of BF3.
* Mon Dec 18 2023 Pak Markthub <pmarkthub@nvidia.com> 2.4.1-%{_release}
- Add support for persistent mapping.
- Fix bug in src/gdrdrv/Makefile.
- Fix compile-time bug when check.h is not found.
* Fri Sep 01 2023 Pak Markthub <pmarkthub@nvidia.com> 2.4-1
- Various bug fixes in the test and benchmark applications.
- Prefix all applications with "gdrcopy_".
- Introduce more unit tests in gdrcopy_sanity.
- Introduce gdrcopy_pplat benchmark application.
- Remove dependency on libcheck and libsubunit
- Introduce gdr_get_info_v2.
- Introduce new copy algorithm for device mappings.
- Add support for NVIDIA BLUEFIELD-3.
- Add support for Linux kernel >= 6.3.
- Add support for SLES and OpenSUSE.
- Add support for systemd service on RHEL9.
- Relicense gdrdrv to Dual MIT/GPL.
- Fix bugs in gdrdrv when pinning two small buffers back-to-back.
- Add support for coherent platforms such as Grace-Hopper.
- Add support for Confidential Computing (CC).
* Fri May 12 2023 Pak Markthub <pmarkthub@nvidia.com> 2.3.1-1
- Add a workaround for the GPL-compatibility issue when compile with CONFIG_ARCH_HAS_CC_PLATFORM on Linux kernel 5.18+.
- Fix error in init.d/gdrcopy due to missing /etc/rc.d/init.d/functions.
* Fri Jul 23 2021 Pak Markthub <pmarkthub@nvidia.com> 2.3-1
- Remove automatically-generated build id links.
- Remove gdrcopy-kmod from the Requires field.
- Add apiperf test.
- Various updates in README.
- Revamp gdrdrv to fix race-condition bugs.
* Mon Feb 01 2021 Pak Markthub <pmarkthub@nvidia.com> 2.2-1
- Add support for ARM64.
- Update various information on README.
- Improve Makefile.
- Add multi-arch support.
- Handle removal of HAVE_UNLOCKED_IOCTL in Linux kernel v5.9 and later.
- Prevent dpkg package creation to unnecessarily compile gdrdrv.
- Improve gdr_open error message.
- Fix bug that prevents sanity from correctly summarizing failure.
- Add dkms support in kmod package.
- Handle the removal of kzfree in Linux kernel v5.10 and later.
- Improve small-size copy-to-mapping.
* Mon Jan 18 2021 Pak Markthub <pmarkthub@nvidia.com> 2.1-2
- Add DKMS support in gdrcopy-kmod.rpm
* Fri Jul 31 2020 Davide Rossetti <drossetti@nvidia.com> 2.1-1
- fix build problem on RHL8 kernels
- relax checks in gdrdrv to support multi-threading use cases
- fix fd leak in gdr_open()
* Mon Mar 02 2020 Davide Rossetti <drossetti@nvidia.com> 2.0-4
- Introduce copylat test application.
- Introduce basic_with_tokens and invalidation_fork_child_gdr_pin_parent_with_tokens sub-tests in sanity.
- Remove the dependency with libcudart.so.
- Clean up the code in the tests folder.
- Change the package maintainer to Davide Rossetti.
* Mon Sep 16 2019 Pak Markthub <pmarkthub@nvidia.com> 2.0-3
- Harden security in gdrdrv.
- Enable cached mappings in POWER9.
- Improve copy performance with unrolling in POWERPC.
- Creates _sanity_ unit test for testing the functionality and security.
- Consolidate basic and _validate_ into sanity unit test.
- Introduce compile time and runtime version checking in libgdrapi.
- Improve rpm packaging.
- Introduce deb packaging for the userspace library and the applications.
- Introduce dkms packaging for the gdrdrv driver.
- Rename gdr_copy_from/to_bar to gdr_copy_from/to_mapping.
- Update README
* Thu Jul 26 2018 Davide Rossetti <davide.rossetti@gmail.com> 1.4-2
- bumped minor version
* Fri Jun 29 2018 Davide Rossetti <davide.rossetti@gmail.com> 1.3-2
- a few bug fixes
* Mon Feb 13 2017 Davide Rossetti <davide.rossetti@gmail.com> 1.2-2
- package libgdrcopy.so as well
- add basic test
* Thu Sep 15 2016 Davide Rossetti <davide.rossetti@gmail.com> 1.2-1
- First version of RPM spec

