# adapted from QE-RPMs jobs (thanks jsefler)
BUILD_ARCHS=x86_64
for ARCH in $BUILD_ARCHS; do
    TARGETDIR=$WORKSPACE/rpms/$ARCH
    mkdir -p $TARGETDIR

    for RPM in *.${ARCH}.rpm; do
        mv $RPM $TARGETDIR/$RPM
        # copying the rpm to a versionless rpm filename allows automated hudson jobs to reference predictable artifacts like...
        # lastSuccessfulBuild/artifact/rpms/x86_64/subscription-manager.rpm
        VERSIONLESS_RPM=`echo $RPM | sed "s/\\(\\($PKG\\(-[a-zA-Z]\\+\\)*\\)\\)-.*/\\1.rpm/"`
        cp $TARGETDIR/$RPM $TARGETDIR/$VERSIONLESS_RPM
    done

    createrepo $TARGETDIR
done