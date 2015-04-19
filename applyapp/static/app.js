( function ( $ ) {
    var uploadedContentDropzone, teachers, $confirmContacted;

    $( '#taking_ap_courses' ).change( function () {
        var checked = $( this ).prop( 'checked' );
        $( '#current_ap_courses' ).parent().toggle( $( this ).prop( 'checked' ) );
        if ( !checked ) {
            $( '#current_ap_courses' ).val( '' );
        }
    } );
    $( '#taking_ap_courses' ).trigger( 'change' );

    $( '#entering_grade option:first' ).attr( 'disabled', 'disabled' );

    $( '#desired_courses label' ).each( function () {
        var $this = $( this ),
            courseLink = '/courses/' + $this.siblings( 'input' ).val(),
            $details = $( '<div>', { class: 'details-div' } ).text( 'Loading...' ).hide(),
            $trigger = $( '<span>' ).append(
                ' (',
                $( '<a>' )
                    .text( 'show details' )
                    .attr( 'href', courseLink )
                    .click( function ( e ) {
                        var $t = $( this );
                        if ( !$t.data( 'state' ) || $t.data( 'state' ) === false ) {
                            $t.data( 'state', true );
                            $t.text( 'hide details' );
                            $details.show();
                        } else {
                            $t.text( 'show details' );
                            $t.data( 'state', false );
                            $details.hide();
                        }
                        e.preventDefault();
                    } ),
                ')' );

        $trigger.one( 'click', function () {
            $details.load( courseLink + ' .info' );
        } );

        $trigger.appendTo( $this );
        $details.insertAfter( $this );
    } );

    teachers = {};
    $confirmContacted = $( '#confirm_contacted' ).parent().parent();
    $confirmContactedClone = $confirmContacted.clone().removeAttr( 'id' );

    $( '#teacher_recs' ).change( function ( e, isInitial ) {
        $( this ).find( 'option' ).each( function () {
            var $originalNode, newText,
                $this = $( this ),
                name = $( this ).text();

            if ( $this.is( ':selected' ) ) {
                if ( !teachers[name ] ) {
                    teachers[name] = $confirmContactedClone.clone().appendTo( '#confirms' );
                    teachers[name].find( 'input' ).prop( 'checked', false );
                    $originalNode = teachers[name].find( 'label' ).contents().last();
                    newText = $originalNode.text().replace( 'TEACHER_NAME', name );
                    $originalNode.remove();
                    teachers[name].find( 'label' ).append( newText );
                }
            } else {
                if ( teachers[name] ) {
                    teachers[name].remove();
                    delete teachers[name];
                }
            }
        } );

        $confirmContacted.find( 'input' ).prop( 'checked', Object.keys( teachers ).length > 0 );
    } );
    $( '#teacher_recs' ).trigger( 'change' );
    $( '#confirms' ).find( 'input' ).prop( 'checked', true );

    $( 'textarea' ).on( 'keyup click', function () {
        $( this ).elastic();
        $( this ).off( 'keyup click' );
    } );

    if ( window.Dropzone ) {
        Dropzone.options.fileUploadDropzone = {
            url: window.location.href,
            uploadMultiple: false,
            dictDefaultMessage: 'Drag and drop files here or click to upload.',
            acceptedFiles: '.doc,.docx',
            addRemoveLinks: true,
            removedfile: function ( file ) {
                var href = window.location.href;
                $.get( href + ( href[href.length - 1] === '/' ? '' : '/' ) + 'delete_file', {
                    name: file.name
                } );
                file.previewElement.parentNode.removeChild( file.previewElement );
            },
            init: function () {
                var dz = this;
                PREV_UPLOADS.forEach( function ( prevFile ) {
                    dz.emit( 'addedfile', prevFile );
                    dz.emit( 'complete', prevFile );
                } );
            }
        };
    }

    if ( $( '#teacher_recs' ).length ) {
        $( '#teacher_recs' )
            .attr( 'data-placeholder', 'Start typing a name...' )
            .chosen( {
                width: '50%',
                no_results_text: 'Oops, no teachers could be found with that name.'
            } );
    }

    $( 'form' ).areYouSure();

    function updateHandlers () {
        $( '.rec-links a' ).off( 'click' );

        $( '.rec-links a' ).not( '.needs-rationale' ).click( function () {
            submitRecommendation( $( this ), this.href );
            return false;
        } );

        $( '.rec-links a.needs-rationale' )
            .click( function () {
                $( 'a.needs-rationale' ).not( this ).popover( 'hide' );
            } )
            .each( function () {
                $( this ).attr( 'title', $( this ).text () );
                $( this ).popover( {
                    html: true,
                    placement: 'auto bottom',
                    content: function () {
                        var $link = $( this ),
                            $textarea = $( '<textarea>', { placeholder: 'Please enter a rationale. Only school ' +
                                'administrators will see the information you provide here.', class: 'rationale-entry' } ),
                            $button = $( '<button>' )
                                .text( $link.text() )
                                .attr( 'class', $link.attr( 'class' ) )
                                .click( function () {
                                    var href = $link.data( 'href' ) + '&rationale=' + encodeURIComponent( $textarea.val() );
                                    submitRecommendation( $link, href );
                                } );

                        $textarea.keyup( function () {
                            $button.prop( 'disabled', $textarea.val().length === 0 );
                        } );
                        $textarea.trigger( 'keyup' );

                        return $( '<div>' ).append(
                            $textarea,
                            $button
                        );
                    }
                } );
            } );
    }
    updateHandlers();

    function submitRecommendation ( $link, href ) {
        var $parent = $link.parent();

        $parent.empty().append( 'Updating...' );

        $.post( href, function ( resp ) {
            $parent.replaceWith( resp );
            updateHandlers();
        } );
    }

    $( 'span.glyphicon' ).text( '' );

}( jQuery ) );