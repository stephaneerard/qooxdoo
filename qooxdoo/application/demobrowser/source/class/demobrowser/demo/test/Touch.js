/* ************************************************************************

   qooxdoo - the new era of web development

   http://qooxdoo.org

   Copyright:
     2004-2008 1&1 Internet AG, Germany, http://www.1und1.de

   License:
     LGPL: http://www.gnu.org/licenses/lgpl.html
     EPL: http://www.eclipse.org/org/documents/epl-v10.php
     See the LICENSE file in the project's top-level directory for details.

   Authors:
     * Tino Butz (tbtz)

************************************************************************ */

qx.Class.define("demobrowser.demo.test.Touch",
{
  extend : qx.application.Native,



  /*
  *****************************************************************************
     MEMBERS
  *****************************************************************************
  */

  members :
  {
  
    __infoAreaOne : null,
    __infoAreaTwo : null,

    /**
     * This method contains the initial application code and gets called 
     * during startup of the application
     * 
     * @lint ignoreDeprecated(alert)
     */
    main : function()
    {
      // Call super class
      this.base(arguments);

      // Enable logging in debug variant
      if (qx.core.Variant.isSet("qx.debug", "on"))
      {
        // support native logging capabilities, e.g. Firebug for Firefox
        qx.log.appender.Native;
        // support additional cross-browser console. Press F7 to toggle visibility
        qx.log.appender.Console;
      }

      var container = new qx.html.Element("div");
      container.useElement(document.body);
      container.setRoot(true);

      container.add(this.__createTouchArea(10,10, "green", "One"));
      container.add(this.__createTouchArea(110,10, "blue", "Two"));

      this.__infoAreaOne = this.__createInfoArea(10,110);
      container.add(this.__infoAreaOne);

      this.__infoAreaTwo = this.__createInfoArea(110, 110);
      container.add(this.__infoAreaTwo);
      
      container.add(this.__createCancelArea(210,10));
    },


    __createTouchArea : function(x, y, color, id)
    {
      var styles = {
        "position" : "absolute",
        "left" : x + "px",
        "top" : y + "px",
        "width" : "90px",
        "height" : "90px",
        "backgroundColor" : color,
        "fontFamily" : "Arial",
        "fontSize" : "12px"
      };

      var area = new qx.html.Element("div", styles, {"id":id});
      area.setAttribute("innerHTML", "<b>Touch me:<br>" + id +"</b>");
      area.addListener("touchstart", this.__refreshInfoArea, this);
      area.addListener("touchmove", this.__refreshInfoArea, this);
      area.addListener("touchend", this.__refreshInfoArea, this);
      area.addListener("touchcancel", this.__refreshInfoArea, this);
      return area;
    },


    __createInfoArea : function(x, y)
    {
      var styles = {
        "position" : "absolute",
        "left" : x + "px",
        "top" : y + "px",
        "width" : "90px",
        "fontFamily" : "Arial",
        "fontSize" : "9px"
      };

      return new qx.html.Element("div", styles);
    },


    __createCancelArea : function(x,y) {
      var styles = {
          "position" : "absolute",
          "left" : x + "px",
          "top" : y + "px",
          "width" : "55px",
          "height" : "55px",
          "backgroundColor" : "red",
          "fontFamily" : "Arial",
          "fontSize" : "12px"
        };
        var cancel = new qx.html.Element("div", styles);
        cancel.setAttribute("innerHTML", "<b>Cancel Touch</b>");
        cancel.addListener("click", function() {
          window.setTimeout(function() {
            alert("Touch canceled");
          },0);
        },this);
        return cancel;
    },


    __refreshInfoArea : function(e)
    {
      var info = [];
      info.push("Type: " + e.getType());
      info.push("==============");
      info.push("Is Multi-Touch: " + e.isMultiTouch());
      info.push("All Touches: " + e.getAllTouches().length);
      info.push("Target Touches: " + e.getTargetTouches().length);
      info.push("Changed Target Touches: " + e.getChangedTargetTouches().length);
      info.push("==============");
      info.push("Document: Left = " + e.getDocumentLeft() + " / Top = " + e.getDocumentTop());
      info.push("Screen: Left = " + e.getScreenLeft() + " / Top = " + e.getScreenTop());
      info.push("Viewport: Left = " + e.getViewportLeft() + " / Top = " + e.getViewportTop());
      info.push("Identifier: " + e.getIdentifier());

      var target = e.getTarget();

      var isTargetTouch = false;
      var targetTouches = e.getTargetTouches().length > 0 ? e.getTargetTouches() : e.getChangedTargetTouches();
      for (var i = 0; i <  targetTouches.length; i++) {

        isTargetTouch = targetTouches[0].target == target;
        if (!isTargetTouch) {
          break;
        }
      }

      info.push("Are all touch targets div " + target.id + ":" + isTargetTouch);

      var infoArea = this["__infoArea" + target.id];
      if (infoArea) {
        infoArea.setAttribute("innerHTML", info.join("<br>"));
      }
    }

  }
});
