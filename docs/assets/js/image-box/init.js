(function ($) {
    "use strict";

    $(window).on('load',function () {
        $('.ct-imageBox').each(function(){
            var $this = $(this);

            var imgLoad = imagesLoaded($this);
            imgLoad.on( 'progress', function( instance, image ) {
                $this.find('.ct-imageBox-inner').css('height', image.img.height);
            })
        })
    })
}(jQuery));