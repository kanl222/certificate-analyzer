%{!?pkg_version:%global pkg_version 0.2.0}
%{!?pkg_release:%global pkg_release 1}
%{!?altlinux:%global altlinux 0}

# PyInstaller bundles Python and extension modules. Do not generate dependencies
# on the build machine's Python ABI or provide its bundled private libraries.
AutoReqProv: no
%global debug_package %{nil}
%global __strip /bin/true

Name: certificate-analyzer
Version: %{pkg_version}
Release: %{pkg_release}
Summary: X.509 certificate and MChD manager
License: Proprietary
Group: Office
URL: https://github.com/kanl222/certificate-analyzer
BuildArch: %{_target_cpu}
Requires: /bin/sh
Requires: /usr/bin/notify-send
Requires: /usr/bin/xdg-open
Requires: /usr/bin/gio
Requires: /usr/bin/fc-match
Requires: libX11.so.6()(64bit)
Requires: libXext.so.6()(64bit)
Requires: libXrender.so.1()(64bit)
Requires: libXft.so.2()(64bit)
Requires: libfontconfig.so.1()(64bit)
Requires: libfreetype.so.6()(64bit)
Requires: libc.so.6()(64bit)
%if %{altlinux}
Requires: fonts-ttf-dejavu
Requires: fonts-ttf-google-noto-sans
%else
Requires: dejavu-sans-fonts
%endif

%description
Certificate and MChD storage, reports and expiration monitoring.
Includes the Python runtime. Monitoring runs in the user's session.
Use requires written permission from the copyright holder; see LICENSE.

%prep

%build

%install
mkdir -p "%{buildroot}/opt/certificate-analyzer"
cp -a "%{bundle_dir}/." "%{buildroot}/opt/certificate-analyzer/"
install -d "%{buildroot}/usr/bin" "%{buildroot}/usr/share/applications"
install -d "%{buildroot}/usr/lib/systemd/user"
install -d "%{buildroot}/usr/share/icons/hicolor/256x256/apps"
install -d "%{buildroot}/usr/share/doc/certificate-analyzer"
ln -s /opt/certificate-analyzer/certificate-analyzer "%{buildroot}/usr/bin/certificate-analyzer"
install -m 0644 "%{project_root}/packaging/linux/certificate-analyzer.desktop" "%{buildroot}/usr/share/applications/"
install -m 0644 "%{project_root}/packaging/linux/certificate-analyzer.service" "%{buildroot}/usr/lib/systemd/user/"
install -m 0644 "%{project_root}/src/certificate_analyzer/assets/app-icon.png" "%{buildroot}/usr/share/icons/hicolor/256x256/apps/certificate-analyzer.png"
install -m 0644 "%{project_root}/LICENSE" "%{buildroot}/usr/share/doc/certificate-analyzer/LICENSE"

%post
if command -v systemctl >/dev/null 2>&1; then
    systemctl --global enable certificate-analyzer.service >/dev/null 2>&1 || :
fi
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database /usr/share/applications >/dev/null 2>&1 || :
fi

%preun
# RPM passes 0 for removal and 1 for replacement during an upgrade.
if [ "$1" -eq 0 ] && command -v systemctl >/dev/null 2>&1; then
    systemctl --global disable certificate-analyzer.service >/dev/null 2>&1 || :
fi

%postun
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database /usr/share/applications >/dev/null 2>&1 || :
fi

%files
%defattr(-,root,root)
/opt/certificate-analyzer
/usr/bin/certificate-analyzer
/usr/share/applications/certificate-analyzer.desktop
/usr/lib/systemd/user/certificate-analyzer.service
/usr/share/icons/hicolor/256x256/apps/certificate-analyzer.png
%doc /usr/share/doc/certificate-analyzer/LICENSE
