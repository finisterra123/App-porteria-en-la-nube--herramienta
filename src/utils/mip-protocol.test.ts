import test from 'node:test';
import assert from 'node:assert/strict';
import {
  getDefaultDoorsList,
  buildAsrCommand,
  formatIdleDisplayMessage,
  analyzeSipAlgResponse,
} from './mip-protocol.ts';

test('getDefaultDoorsList returns MIP base doors and RS-485 XRE modules', () => {
  const doors = getDefaultDoorsList();
  assert.ok(doors.length >= 6);

  const mipDoor = doors.find((d) => d.devAddr === 1 && d.relay === 1);
  assert.ok(mipDoor);
  assert.equal(mipDoor?.type, 'MIP Placa Base');

  const xre1 = doors.find((d) => d.devAddr === 2 && d.relay === 1);
  assert.ok(xre1);
  assert.equal(xre1?.type, 'XRE 1000 Plus');

  const xre2 = doors.find((d) => d.devAddr === 3 && d.relay === 1);
  assert.ok(xre2);
  assert.equal(xre2?.type, 'XRE 1000 Plus');
});

test('buildAsrCommand builds valid hex frame and description', () => {
  const cmdMip = buildAsrCommand(1, 1);
  assert.ok(cmdMip.hexCommand.includes('02 18 01 01'));
  assert.ok(cmdMip.log.includes('MIP 1000 IP'));

  const cmdXre = buildAsrCommand(3, 2);
  assert.ok(cmdXre.hexCommand.includes('02 18 03 02'));
  assert.ok(cmdXre.log.includes('Módulo RS-485 Dir 3'));
});

test('formatIdleDisplayMessage truncates to 20 uppercase characters', () => {
  const normal = formatIdleDisplayMessage('Porteria En La Nube');
  assert.equal(normal.validText, 'PORTERIA EN LA NUBE');
  assert.equal(normal.isTruncated, false);

  const longText = formatIdleDisplayMessage('Bienvenidos al condominio campestre torre residencial');
  assert.equal(longText.validText.length, 20);
  assert.equal(longText.isTruncated, true);
});

test('analyzeSipAlgResponse detects header alteration', () => {
  const cleanResp =
    'SIP/2.0 200 OK\r\nVia: SIP/2.0/UDP 192.168.1.105:5072;branch=z9hG4bK123\r\nContent-Length: 0\r\n\r\n';
  const cleanAnalysis = analyzeSipAlgResponse(cleanResp, '192.168.1.105', 5072);
  assert.equal(cleanAnalysis.sipAlgDetected, false);

  const alteredResp =
    'SIP/2.0 200 OK\r\nVia: SIP/2.0/UDP 181.49.20.14:5072;branch=z9hG4bK123\r\nContent-Length: 0\r\n\r\n';
  const algAnalysis = analyzeSipAlgResponse(alteredResp, '192.168.1.105', 5072);
  assert.equal(algAnalysis.sipAlgDetected, true);
  assert.match(algAnalysis.explanation, /INDICIO DE SIP ALG ACTIVO/);
});
