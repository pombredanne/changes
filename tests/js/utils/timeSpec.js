define(['app', 'utils/time'], function(app, time) {
  'use strict';

  describe('duration', function() {
    it('should support milliseconds', function() {
      var result = time.duration(320);
      expect(result).to.equal('320 ms');

      var result = time.duration(1);
      expect(result).to.equal('1 ms');
    });

    it('should support seconds', function() {
      var result = time.duration(3200);
      expect(result).to.equal('3.2 sec');

      var result = time.duration(120000);
      expect(result).to.equal('120 sec');
    });

    it('should support minutes', function() {
      var result = time.duration(180000);
      expect(result).to.equal('3 min');

      var result = time.duration(360000);
      expect(result).to.equal('6 min');

      var result = time.duration(3600000);
      expect(result).to.equal('60 min');

      var result = time.duration(7200000);
      expect(result).to.equal('120 min');
    });

    it('should support hours', function() {
      var result = time.duration(14400000);
      expect(result).to.equal('4 hr');
    });
  });

  describe('timeSince', function() {
    var now;

    beforeEach(function(){
      // There is probably an API thats exposed for this
      now = moment.utc()._d.getTime();
    });

    it('should support seconds', function() {
      var result = time.timeSince(now - 1000, now);
      expect(result).to.equal('just now');

      var result = time.timeSince(now + 1000, now);
      expect(result).to.equal('just now');

      var result = time.timeSince(now - 3200, now);
      expect(result).to.equal('just now');
    });

    it('should support minutes', function() {
      var result = time.timeSince(now - 60001, now);
      expect(result).to.equal('1 minute ago');

      var result = time.timeSince(now - 120000, now);
      expect(result).to.equal('2 minutes ago');

      var result = time.timeSince(now - 180000, now);
      expect(result).to.equal('3 minutes ago');

      var result = time.timeSince(now - 360000, now);
      expect(result).to.equal('6 minutes ago');

      var result = time.timeSince(now - 3600000, now);
      expect(result).to.equal('60 minutes ago');

      var result = time.timeSince(now - 7200000, now);
      expect(result).to.equal('120 minutes ago');
    });

    it('should support hours', function() {
      var result = time.timeSince(now - 14400000, now);
      expect(result).to.equal('4 hours ago');
    });

    it('should support dates', function() {
      var result = time.timeSince(now - 3456000000, now);
      expect(result).to.not.equal('4 hours ago');
    });
  });
});
